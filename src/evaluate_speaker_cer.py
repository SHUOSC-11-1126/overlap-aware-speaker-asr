from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .evaluate_cer import (
    levenshtein_distance,
    list_verified_cases,
    load_json,
    load_reference,
    normalize_text,
)


CSV_COLUMNS = [
    "case_id",
    "method",
    "speaker_1_cer",
    "speaker_2_cer",
    "speaker_macro_cer",
    "speaker_gap",
    "speaker_1_reference_length",
    "speaker_2_reference_length",
    "speaker_1_hypothesis_length",
    "speaker_2_hypothesis_length",
    "observation",
]


METHOD_ORDER = ["separated_whisper", "separated_whisper_cleaned"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate speaker-aware CER for verified cases.")
    parser.add_argument("--case", required=True, help="Audio case id, e.g. NoOverlap, LightOverlap, or all")
    return parser.parse_args()


def compute_cer(reference_text: str, hypothesis_text: str) -> dict[str, Any]:
    ref_norm = normalize_text(reference_text)
    hyp_norm = normalize_text(hypothesis_text)
    distance = levenshtein_distance(ref_norm, hyp_norm)
    reference_length = len(ref_norm)
    cer = round(distance / reference_length, 6) if reference_length else 0.0
    return {
        "normalized_reference": ref_norm,
        "normalized_hypothesis": hyp_norm,
        "reference_length": reference_length,
        "hypothesis_length": len(hyp_norm),
        "edit_distance": distance,
        "cer": cer,
    }


def aggregate_speaker_text(segments: list[dict[str, Any]], speaker: str) -> str:
    texts: list[str] = []
    for segment in segments:
        if str(segment.get("speaker", "")).upper() == speaker:
            text = str(segment.get("text", "")).strip()
            if text:
                texts.append(text)
    return "".join(texts)


def load_speaker_transcript(case_id: str, method: str) -> tuple[Path, dict[str, Any]]:
    if method == "separated_whisper":
        path = PROJECT_ROOT / "results" / "transcripts_speaker" / f"{case_id}_separated_speaker_transcript.json"
        if not path.exists():
            raise FileNotFoundError(f"Missing speaker transcript: {path.relative_to(PROJECT_ROOT)}")
        return path, load_json(path)

    if method == "separated_whisper_cleaned":
        path = (
            PROJECT_ROOT
            / "results"
            / "transcripts_postprocessed"
            / f"{case_id}_separated_speaker_transcript_cleaned.json"
        )
        if not path.exists():
            raise FileNotFoundError(f"Missing cleaned speaker transcript: {path.relative_to(PROJECT_ROOT)}")
        return path, load_json(path)

    raise ValueError(f"Unsupported speaker-aware method: {method}")


def build_row(case_id: str, method: str) -> dict[str, Any]:
    reference = load_reference(case_id)
    speaker_1_reference_text = str(reference.get("speaker_1_text", ""))
    speaker_2_reference_text = str(reference.get("speaker_2_text", ""))

    transcript_path, transcript = load_speaker_transcript(case_id, method)
    if method == "separated_whisper":
        segments = transcript.get("segments", [])
    else:
        segments = transcript.get("cleaned_segments", [])

    speaker_1_hypothesis_text = aggregate_speaker_text(segments, "SPEAKER_1")
    speaker_2_hypothesis_text = aggregate_speaker_text(segments, "SPEAKER_2")

    s1_metrics = compute_cer(speaker_1_reference_text, speaker_1_hypothesis_text)
    s2_metrics = compute_cer(speaker_2_reference_text, speaker_2_hypothesis_text)

    speaker_1_cer = s1_metrics["cer"]
    speaker_2_cer = s2_metrics["cer"]
    speaker_macro_cer = round((speaker_1_cer + speaker_2_cer) / 2, 6)
    speaker_gap = round(abs(speaker_1_cer - speaker_2_cer), 6)

    observation_parts = [
        "Speaker-aware CER checks whether the method preserves who said what.",
    ]
    if method == "separated_whisper_cleaned":
        removed_count = int(transcript.get("removed_count", 0) or 0)
        if removed_count:
            observation_parts.append(
                f"Cleaning removed {removed_count} repeated segments, which may reduce hallucinations."
            )
        else:
            observation_parts.append("Cleaning did not remove any segments for this case.")
    if speaker_gap >= 0.15:
        observation_parts.append("Large speaker gap indicates uneven recognition quality between speakers.")
    else:
        observation_parts.append("Speaker quality is relatively balanced across the two speakers.")

    return {
        "case_id": case_id,
        "method": method,
        "speaker_1_cer": speaker_1_cer,
        "speaker_2_cer": speaker_2_cer,
        "speaker_macro_cer": speaker_macro_cer,
        "speaker_gap": speaker_gap,
        "speaker_1_reference_length": s1_metrics["reference_length"],
        "speaker_2_reference_length": s2_metrics["reference_length"],
        "speaker_1_hypothesis_length": s1_metrics["hypothesis_length"],
        "speaker_2_hypothesis_length": s2_metrics["hypothesis_length"],
        "observation": " ".join(observation_parts),
    }


def read_existing_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    if path.suffix.lower() == ".csv":
        with path.open("r", newline="", encoding="utf-8-sig") as f:
            try:
                for row in csv.DictReader(f):
                    if isinstance(row, dict):
                        rows.append(row)
            except csv.Error as exc:
                print(f"warning: failed to parse CSV {path.relative_to(PROJECT_ROOT)}: {exc}")
        return rows
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            print(f"warning: failed to parse JSON {path.relative_to(PROJECT_ROOT)}: {exc}")
            return rows
        if isinstance(payload, list):
            rows.extend(item for item in payload if isinstance(item, dict))
        elif isinstance(payload, dict):
            maybe_rows = payload.get("rows")
            if isinstance(maybe_rows, list):
                rows.extend(item for item in maybe_rows if isinstance(item, dict))
        return rows
    return rows


def sanitize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for idx, row in enumerate(rows):
        case_id = str(row.get("case_id", "")).strip()
        method = str(row.get("method", "")).strip()
        if not case_id or not method:
            print(f"warning: skipping bad existing row at index {idx}: {row}")
            continue
        key = (case_id, method)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(row)
    return cleaned


def upsert_row(rows: list[dict[str, Any]], row: dict[str, Any]) -> list[dict[str, Any]]:
    key = (str(row.get("case_id", "")), str(row.get("method", "")))
    filtered = [
        existing
        for existing in rows
        if (str(existing.get("case_id", "")), str(existing.get("method", ""))) != key
    ]
    filtered.append(row)
    return sorted(filtered, key=lambda item: (str(item.get("case_id", "")), str(item.get("method", ""))))


def rows_for_cases(cases: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case_id in cases:
        for method in METHOD_ORDER:
            try:
                rows.append(build_row(case_id, method))
            except FileNotFoundError as exc:
                print(f"warning: skipping {case_id} {method}: {exc}")
    return rows


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    output_dir = PROJECT_ROOT / "results" / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "speaker_cer_results.csv"
    json_path = output_dir / "speaker_cer_results.json"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_path, json_path


def plot_results(rows: list[dict[str, Any]]) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir = PROJECT_ROOT / "results" / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / "speaker_cer_by_case.png"

    cases = sorted({str(row["case_id"]) for row in rows})
    method_to_values: dict[str, list[float]] = defaultdict(list)
    for case_id in cases:
        case_rows = {str(row["method"]): row for row in rows if str(row["case_id"]) == case_id}
        for method in METHOD_ORDER:
            value = case_rows.get(method)
            method_to_values[method].append(float(value["speaker_macro_cer"]) if value else 0.0)

    x = list(range(len(cases)))
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 5))
    offsets = [(-width / 2), (width / 2)]
    colors = ["#4C78A8", "#F58518"]
    for idx, method in enumerate(METHOD_ORDER):
        ax.bar(
            [pos + offsets[idx] for pos in x],
            method_to_values[method],
            width=width,
            label=method,
            color=colors[idx],
        )

    ax.set_xticks(x)
    ax.set_xticklabels(cases, rotation=20, ha="right")
    ax.set_ylabel("Speaker Macro CER")
    ax.set_title("Speaker-aware CER by Case")
    ax.legend()
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(png_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return png_path


def render_markdown(rows: list[dict[str, Any]], figure_path: Path, csv_path: Path) -> Path:
    output_dir = PROJECT_ROOT / "results" / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / "speaker_cer_summary.md"

    by_case: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_case[str(row["case_id"])][str(row["method"])] = row

    avg_by_method: dict[str, float] = {}
    for method in METHOD_ORDER:
        values = [float(row["speaker_macro_cer"]) for row in rows if str(row["method"]) == method]
        avg_by_method[method] = round(sum(values) / len(values), 6) if values else 0.0

    largest_gap_case = max(rows, key=lambda row: float(row["speaker_gap"])) if rows else None

    lines: list[str] = []
    lines.append("# Speaker-aware CER Summary")
    lines.append("")
    lines.append("## Why speaker-aware CER matters")
    lines.append("")
    lines.append(
        "Normal CER only checks whether the words match, but it does not tell us whether the right speaker's content was preserved. "
        "Speaker-aware CER measures each speaker track separately, which is useful for assessing speaker attribution quality."
    )
    lines.append("")
    lines.append("## Average speaker macro CER")
    lines.append("")
    for method in METHOD_ORDER:
        lines.append(f"- {method}: {avg_by_method[method]}")
    lines.append("")
    if largest_gap_case is not None:
        lines.append("## Largest speaker gap")
        lines.append("")
        lines.append(
            f"- {largest_gap_case['case_id']} / {largest_gap_case['method']}: {largest_gap_case['speaker_gap']}"
        )
        lines.append("")
    lines.append("## Per-case results")
    lines.append("")
    lines.append("| case_id | method | speaker_1_cer | speaker_2_cer | speaker_macro_cer | speaker_gap |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: |")
    for case_id in sorted(by_case):
        for method in METHOD_ORDER:
            row = by_case[case_id][method]
            lines.append(
                f"| {case_id} | {method} | {row['speaker_1_cer']} | {row['speaker_2_cer']} | "
                f"{row['speaker_macro_cer']} | {row['speaker_gap']} |"
            )
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"- Speaker CER CSV: {csv_path.relative_to(PROJECT_ROOT).as_posix()}")
    lines.append(f"- Speaker CER figure: {figure_path.relative_to(PROJECT_ROOT).as_posix()}")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def update_current_summary(rows: list[dict[str, Any]], summary_md_path: Path, figure_path: Path) -> None:
    current_path = PROJECT_ROOT / "results" / "figures" / "current_results_summary.md"
    if current_path.exists():
        text = current_path.read_text(encoding="utf-8-sig")
    else:
        text = "# Current Results Summary\n"

    marker = "## Speaker-aware Evaluation\n"
    if marker in text:
        text = text.split(marker)[0].rstrip()

    avg_by_method: dict[str, float] = {}
    for method in METHOD_ORDER:
        values = [float(row["speaker_macro_cer"]) for row in rows if str(row["method"]) == method]
        avg_by_method[method] = round(sum(values) / len(values), 6) if values else 0.0

    largest_gap_case = max(rows, key=lambda row: float(row["speaker_gap"])) if rows else None

    lines: list[str] = []
    lines.append("")
    lines.append("## Speaker-aware Evaluation")
    lines.append("")
    lines.append(
        "- Normal CER can miss speaker attribution problems because it collapses the transcript into one string."
    )
    lines.append(
        "- Speaker-aware CER compares each speaker track separately, so we can see whether a method preserves who said what."
    )
    lines.append("- Separated speaker-track ASR is useful, but cleaned transcripts can trade repetition reduction for content loss.")
    lines.append("")
    lines.append("### Average speaker macro CER")
    lines.append("")
    for method in METHOD_ORDER:
        lines.append(f"- {method}: {avg_by_method[method]}")
    lines.append("")
    if largest_gap_case is not None:
        lines.append("### Largest speaker gap")
        lines.append("")
        lines.append(
            f"- {largest_gap_case['case_id']} / {largest_gap_case['method']}: {largest_gap_case['speaker_gap']}"
        )
    lines.append("")
    lines.append(
        f"- Detailed speaker-aware table: {summary_md_path.relative_to(PROJECT_ROOT).as_posix()}"
    )
    lines.append(f"- Speaker-aware plot: {figure_path.relative_to(PROJECT_ROOT).as_posix()}")

    current_path.write_text(text.rstrip() + "\n" + "\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    _ = load_config()

    if args.case == "all":
        cases = list_verified_cases()
    else:
        cases = [args.case]

    output_csv = PROJECT_ROOT / "results" / "tables" / "speaker_cer_results.csv"
    output_json = PROJECT_ROOT / "results" / "tables" / "speaker_cer_results.json"
    existing_rows = sanitize_rows(read_existing_rows(output_csv))
    json_rows = sanitize_rows(read_existing_rows(output_json))
    existing_rows.extend(json_rows)
    rows = sanitize_rows(existing_rows)
    for row in rows_for_cases(cases):
        rows = upsert_row(rows, row)

    csv_path, json_path = write_outputs(rows)
    figure_path = plot_results(rows)
    speaker_md_path = render_markdown(rows, figure_path, csv_path)
    update_current_summary(rows, speaker_md_path, figure_path)

    print(f"Wrote speaker CER CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker CER JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker CER figure: {figure_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker CER summary: {speaker_md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
