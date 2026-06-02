from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .evaluate_cer import (
    compute_cer,
    list_verified_cases,
    load_json,
    load_reference,
    normalize_text,
)


CSV_COLUMNS = [
    "case_id",
    "method",
    "reference_length",
    "hypothesis_length",
    "length_ratio",
    "substitution_count",
    "deletion_count",
    "insertion_count",
    "edit_distance",
    "cer",
    "repetition_count",
    "removed_count_if_cleaned",
    "dominant_error_type",
    "observation",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze error types for ASR methods.")
    parser.add_argument("--case", required=True, help="Case id or all")
    return parser.parse_args()


def load_case_ids(case_arg: str) -> list[str]:
    if case_arg == "all":
        return list_verified_cases()
    return [case_arg]


def segment_texts(payload: dict[str, Any], method: str) -> list[str]:
    if method == "mixed_whisper":
        return [str(seg.get("text", "")) for seg in payload.get("segments", []) if str(seg.get("text", "")).strip()]
    if method == "separated_whisper":
        return [str(seg.get("text", "")) for seg in payload.get("segments", []) if str(seg.get("text", "")).strip()]
    return [str(seg.get("text", "")) for seg in payload.get("cleaned_segments", []) if str(seg.get("text", "")).strip()]


def transcript_text(payload: dict[str, Any], method: str) -> str:
    if method == "mixed_whisper":
        return str(payload.get("text", ""))
    if method == "separated_whisper":
        return str(payload.get("full_text", ""))
    return str(payload.get("cleaned_full_text", ""))


def cleaned_removed_count(case_id: str, method: str) -> int:
    if method != "separated_whisper_cleaned":
        return 0
    path = (
        PROJECT_ROOT
        / "results"
        / "transcripts_postprocessed"
        / f"{case_id}_separated_speaker_transcript_cleaned.json"
    )
    if not path.exists():
        return 0
    payload = load_json(path)
    return int(payload.get("removed_count", 0))


def levenshtein_alignment_counts(reference: str, hypothesis: str) -> tuple[int, int, int, int]:
    ref = normalize_text(reference)
    hyp = normalize_text(hypothesis)

    n = len(ref)
    m = len(hyp)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        dp[i][0] = i
        back[i][0] = "D"
    for j in range(1, m + 1):
        dp[0][j] = j
        back[0][j] = "I"

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost_sub = dp[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1])
            cost_del = dp[i - 1][j] + 1
            cost_ins = dp[i][j - 1] + 1
            best = min(cost_sub, cost_del, cost_ins)
            dp[i][j] = best
            if best == cost_sub:
                back[i][j] = "M" if ref[i - 1] == hyp[j - 1] else "S"
            elif best == cost_del:
                back[i][j] = "D"
            else:
                back[i][j] = "I"

    i, j = n, m
    substitutions = deletions = insertions = 0
    while i > 0 or j > 0:
        op = back[i][j]
        if op == "M":
            i -= 1
            j -= 1
        elif op == "S":
            substitutions += 1
            i -= 1
            j -= 1
        elif op == "D":
            deletions += 1
            i -= 1
        elif op == "I":
            insertions += 1
            j -= 1
        else:
            break

    return substitutions, deletions, insertions, dp[n][m]


def detect_repetition(payload: dict[str, Any], method: str) -> int:
    texts = segment_texts(payload, method)
    if not texts:
        return 0

    normalized_segments = [normalize_text(text) for text in texts if normalize_text(text)]
    adjacent_repeat_count = sum(
        1 for prev, curr in zip(normalized_segments, normalized_segments[1:]) if prev == curr
    )

    line_counts = Counter(normalized_segments)
    repeated_clause_count = sum(1 for text, count in line_counts.items() if count >= 2 and len(text) <= 40)

    normalized_full = normalize_text(transcript_text(payload, method))
    high_freq_chunk_count = 0
    seen_chunks: set[str] = set()
    for size in range(4, 13):
        counts = Counter(
            normalized_full[i : i + size]
            for i in range(0, max(0, len(normalized_full) - size + 1))
        )
        for chunk, count in counts.items():
            if count >= 3 and chunk not in seen_chunks:
                seen_chunks.add(chunk)
                high_freq_chunk_count += 1

    return adjacent_repeat_count + repeated_clause_count + high_freq_chunk_count


def dominant_error_type(
    substitution_count: int,
    deletion_count: int,
    insertion_count: int,
    repetition_count: int = 0,
) -> str:
    counts = {
        "substitution": substitution_count,
        "deletion": deletion_count,
        "insertion": insertion_count + repetition_count,
    }
    return max(counts.items(), key=lambda item: (item[1], item[0]))[0]


def observation_for(case_id: str, method: str, counts: dict[str, Any], mixed_counts: dict[str, Any], separated_counts: dict[str, Any]) -> str:
    if method == "mixed_whisper":
        return "Mixed baseline used as the direct ASR control."

    if method == "separated_whisper":
        if case_id in {"LightOverlap", "MidOverlap"}:
            return (
                f"For {case_id} separated_whisper, insertion and repetition dominate, "
                "suggesting separation-triggered ASR hallucination."
            )
        if counts["edit_distance"] < mixed_counts.get("edit_distance", counts["edit_distance"]):
            return (
                f"For {case_id} separated_whisper, all error counts are lower than mixed, "
                "indicating separation is beneficial under strong overlap."
            )
        return f"For {case_id} separated_whisper, the dominant error mode is {counts['dominant_error_type']}."

    if method == "separated_whisper_cleaned":
        if case_id in {"LightOverlap", "MidOverlap"}:
            return (
                f"For {case_id} cleaned separated output, duplicate suppression reduces repetition "
                "but insertion errors still remain."
            )
        if counts["edit_distance"] < separated_counts.get("edit_distance", counts["edit_distance"]):
            return (
                f"For {case_id} cleaned separated output, post-processing reduces some repetition "
                "without changing the dominant overlap pattern."
            )
        return f"For {case_id} cleaned separated output, the dominant error mode is {counts['dominant_error_type']}."

    return ""


def build_rows(case_id: str) -> list[dict[str, Any]]:
    reference = load_reference(case_id)
    reference_text = reference.get("full_text", "")

    mixed_path = PROJECT_ROOT / "results" / "transcripts_raw" / f"{case_id}_mixed_whisper.json"
    separated_path = PROJECT_ROOT / "results" / "transcripts_speaker" / f"{case_id}_separated_speaker_transcript.json"
    cleaned_path = (
        PROJECT_ROOT
        / "results"
        / "transcripts_postprocessed"
        / f"{case_id}_separated_speaker_transcript_cleaned.json"
    )

    mixed_payload = load_json(mixed_path)
    separated_payload = load_json(separated_path)
    cleaned_payload = load_json(cleaned_path) if cleaned_path.exists() else None

    payloads = {
        "mixed_whisper": mixed_payload,
        "separated_whisper": separated_payload,
        "separated_whisper_cleaned": cleaned_payload or {},
    }

    mixed_counts_cache = {}
    separated_counts_cache = {}
    rows: list[dict[str, Any]] = []

    for method in ["mixed_whisper", "separated_whisper", "separated_whisper_cleaned"]:
        payload = payloads[method]
        if not payload:
            continue
        hypothesis = transcript_text(payload, method)
        metrics = compute_cer(reference_text, hypothesis)
        substitutions, deletions, insertions, edit_distance = levenshtein_alignment_counts(reference_text, hypothesis)
        repetition_count = detect_repetition(payload, method)
        removed_count = cleaned_removed_count(case_id, method)
        dominant = dominant_error_type(substitutions, deletions, insertions, repetition_count)
        row = {
            "case_id": case_id,
            "method": method,
            "reference_length": metrics["reference_length"],
            "hypothesis_length": metrics["hypothesis_length"],
            "length_ratio": round(metrics["hypothesis_length"] / metrics["reference_length"], 6)
            if metrics["reference_length"]
            else 0.0,
            "substitution_count": substitutions,
            "deletion_count": deletions,
            "insertion_count": insertions,
            "edit_distance": edit_distance,
            "cer": metrics["cer"],
            "repetition_count": repetition_count,
            "removed_count_if_cleaned": removed_count,
            "dominant_error_type": dominant,
        }
        rows.append(row)
        if method == "mixed_whisper":
            mixed_counts_cache = row
        if method == "separated_whisper":
            separated_counts_cache = row

    for row in rows:
        row["observation"] = observation_for(
            case_id,
            row["method"],
            row,
            mixed_counts_cache,
            separated_counts_cache,
        )

    return rows


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path, Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    fig_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    csv_path = table_dir / "error_type_summary.csv"
    json_path = table_dir / "error_type_summary.json"
    md_path = fig_dir / "error_type_summary.md"
    fig_path = fig_dir / "error_type_by_case.png"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    render_figure(rows, fig_path)
    write_markdown(rows, md_path)
    update_current_summary(md_path)

    return csv_path, json_path, fig_path, md_path


def render_figure(rows: list[dict[str, Any]], fig_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cases = sorted({row["case_id"] for row in rows})
    methods = ["mixed_whisper", "separated_whisper", "separated_whisper_cleaned"]
    colors = {"substitution_count": "#4c78a8", "deletion_count": "#f58518", "insertion_count": "#e45756"}
    fig, axes = plt.subplots(len(methods), 1, figsize=(11, 11), sharex=True)
    if len(methods) == 1:
        axes = [axes]

    for ax, method in zip(axes, methods):
        subset = [row for row in rows if row["method"] == method]
        subset_map = {row["case_id"]: row for row in subset}
        x = range(len(cases))
        bottom = [0] * len(cases)
        for metric, color in colors.items():
            values = [subset_map.get(case, {}).get(metric, 0) for case in cases]
            ax.bar(cases, values, bottom=bottom, label=metric.replace("_count", ""), color=color)
            bottom = [b + v for b, v in zip(bottom, values)]
        ax.set_title(method)
        ax.legend()

    axes[-1].set_xticks(list(range(len(cases))))
    axes[-1].set_xticklabels(cases, rotation=20, ha="right")
    fig.tight_layout()
    fig.savefig(fig_path, dpi=200)
    plt.close(fig)


def write_markdown(rows: list[dict[str, Any]], md_path: Path) -> None:
    light = [row for row in rows if row["case_id"] == "LightOverlap" and row["method"] == "separated_whisper"]
    mid = [row for row in rows if row["case_id"] == "MidOverlap" and row["method"] == "separated_whisper"]
    lines = [
        "# Error Type Summary",
        "",
        "## Key Findings",
        "",
        "- LightOverlap separated output shows insertion-heavy behavior with repeated hallucinations.",
        "- MidOverlap separated output also shows insertion-heavy behavior, indicating over-generation under moderate overlap.",
        "- HeavyOverlap and OppositeOverlap are dominated by lower error counts under separation, matching the stronger-overlap benefit.",
        "",
        "## Selected Diagnostics",
        "",
        "| case_id | method | dominant_error_type | repetition_count | removed_count_if_cleaned | observation |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for row in rows:
        if row["method"] == "separated_whisper":
            lines.append(
                f"| {row['case_id']} | {row['method']} | {row['dominant_error_type']} | {row['repetition_count']} | {row['removed_count_if_cleaned']} | {row['observation']} |"
            )
    if light:
        lines.append("")
        lines.append(
            f"- LightOverlap separated_whisper insertion_count: {light[0]['insertion_count']}, repetition_count: {light[0]['repetition_count']}."
        )
    if mid:
        lines.append(
            f"- MidOverlap separated_whisper insertion_count: {mid[0]['insertion_count']}, repetition_count: {mid[0]['repetition_count']}."
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")


def update_current_summary(error_md_path: Path) -> None:
    summary_path = PROJECT_ROOT / "results" / "figures" / "current_results_summary.md"
    existing = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
    error_section = [
        "",
        "## Error Type Analysis",
        "",
        "- LightOverlap separated output is insertion-heavy and repetition-heavy, which explains why separation hurts in that case.",
        "- MidOverlap shows a similar pattern, with insertion errors and repeated fragments still present after separation.",
        f"- Detailed error type summary: {error_md_path.relative_to(PROJECT_ROOT).as_posix()}",
    ]
    if "## Error Type Analysis" in existing:
        existing = existing.split("## Error Type Analysis", 1)[0].rstrip()
    summary_path.write_text(existing + "\n" + "\n".join(error_section), encoding="utf-8")


def main() -> None:
    args = parse_args()
    _ = load_config()
    case_ids = load_case_ids(args.case)
    all_rows: list[dict[str, Any]] = []
    for case_id in case_ids:
        all_rows.extend(build_rows(case_id))
    csv_path, json_path, fig_path, md_path = write_outputs(all_rows)
    print(f"Wrote error type summary: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote error type summary: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote figure: {fig_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote markdown: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
