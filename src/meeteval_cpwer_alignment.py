from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .evaluate_cer import levenshtein_distance, load_reference, normalize_text
from .export_meeteval_compatibility import load_hypothesis_payload


ALIGNMENT_COLUMNS = [
    "case_id",
    "hypothesis_source",
    "cpwer_bridge_lite",
    "speaker_macro_cer",
    "alignment_gap",
    "alignment_status",
    "observation",
]

SUMMARY_COLUMNS = [
    "scope",
    "case_count",
    "matched_count",
    "average_alignment_gap",
    "observation",
]


def compute_cer(reference_text: str, hypothesis_text: str) -> float:
    ref_norm = normalize_text(reference_text)
    hyp_norm = normalize_text(hypothesis_text)
    distance = levenshtein_distance(ref_norm, hyp_norm)
    reference_length = len(ref_norm)
    return round(distance / reference_length, 6) if reference_length else 0.0


def aggregate_speaker_text(segments: list[dict[str, Any]], speaker: str) -> str:
    texts: list[str] = []
    for segment in segments:
        if str(segment.get("speaker", "")).upper() == speaker:
            text = str(segment.get("text", "")).strip()
            if text:
                texts.append(text)
    return "".join(texts)


def build_speaker_macro_cer(case_id: str, method: str) -> float:
    reference = load_reference(case_id)
    payload = load_hypothesis_payload(case_id)
    segments_key = "segments" if method == "separated_whisper" else "cleaned_segments"
    segments = list(payload.get(segments_key, payload.get("segments", [])))
    speaker_1_cer = compute_cer(
        str(reference.get("speaker_1_text", "")),
        aggregate_speaker_text(segments, "SPEAKER_1"),
    )
    speaker_2_cer = compute_cer(
        str(reference.get("speaker_2_text", "")),
        aggregate_speaker_text(segments, "SPEAKER_2"),
    )
    return round((speaker_1_cer + speaker_2_cer) / 2, 6)


def load_cpwer_bridge_rows() -> list[dict[str, Any]]:
    bridge_path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_bridge.json"
    if not bridge_path.exists():
        return []
    payload = json.loads(bridge_path.read_text(encoding="utf-8"))
    return list(payload) if isinstance(payload, list) else [payload]


def build_alignment_row(
    bridge_row: dict[str, Any],
    speaker_macro_cer: float | None = None,
) -> dict[str, Any]:
    case_id = str(bridge_row.get("case_id", ""))
    hypothesis_source = str(bridge_row.get("hypothesis_source", ""))
    cpwer_bridge_lite = float(bridge_row.get("cpwer_bridge_lite", 0.0) or 0.0)
    if speaker_macro_cer is None:
        speaker_macro_cer = build_speaker_macro_cer(case_id, hypothesis_source)
    alignment_gap = round(abs(cpwer_bridge_lite - speaker_macro_cer), 6)
    alignment_status = "matched" if alignment_gap <= 0.001 else "drift"
    return {
        "case_id": case_id,
        "hypothesis_source": hypothesis_source,
        "cpwer_bridge_lite": cpwer_bridge_lite,
        "speaker_macro_cer": speaker_macro_cer,
        "alignment_gap": alignment_gap,
        "alignment_status": alignment_status,
        "observation": (
            "experimental/frontier cross-metric alignment between cpWER bridge-lite and speaker_macro_cer; "
            "this is not a MeetEval benchmark claim."
        ),
    }


def build_alignment_summary_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "scope": "all_gold_cases",
            "case_count": 0,
            "matched_count": 0,
            "average_alignment_gap": 0.0,
            "observation": "No alignment rows were available for summary.",
        }
    matched_count = sum(1 for row in rows if str(row.get("alignment_status", "")) == "matched")
    average_gap = round(
        sum(float(row.get("alignment_gap", 0.0) or 0.0) for row in rows) / len(rows),
        6,
    )
    return {
        "scope": "all_gold_cases",
        "case_count": len(rows),
        "matched_count": matched_count,
        "average_alignment_gap": average_gap,
        "observation": (
            "Cross-metric alignment audit between cpWER bridge-lite and speaker-aware CER baseline; "
            "drift highlights where the bridge-lite export path diverges from the stable speaker_macro_cer view."
        ),
    }


def build_alignment_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Alignment",
        "",
        "This generated note compares cpWER bridge-lite against speaker_macro_cer. "
        "It does not claim a finished MeetEval evaluation.",
        "",
        "| case_id | hypothesis_source | cpwer_bridge_lite | speaker_macro_cer | alignment_gap | alignment_status | observation |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['hypothesis_source']} | {row['cpwer_bridge_lite']} | "
            f"{row['speaker_macro_cer']} | {row['alignment_gap']} | {row['alignment_status']} | {row['observation']} |"
        )
    return lines


def build_alignment_summary_lines(row: dict[str, Any]) -> list[str]:
    lines = [
        "# MeetEval cpWER Alignment Summary",
        "",
        "This generated note summarizes cross-metric alignment across the gold scope.",
        "",
        "| scope | case_count | matched_count | average_alignment_gap | observation |",
        "| --- | ---: | ---: | ---: | --- |",
        (
            f"| {row['scope']} | {row['case_count']} | {row['matched_count']} | "
            f"{row['average_alignment_gap']} | {row['observation']} |"
        ),
    ]
    return lines


def write_outputs(
    rows: list[dict[str, Any]],
    summary_row: dict[str, Any],
) -> tuple[Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    alignment_csv_path = tables_dir / "meeteval_cpwer_alignment.csv"
    alignment_json_path = tables_dir / "meeteval_cpwer_alignment.json"
    alignment_md_path = figures_dir / "meeteval_cpwer_alignment.md"
    summary_csv_path = tables_dir / "meeteval_cpwer_alignment_summary.csv"
    summary_json_path = tables_dir / "meeteval_cpwer_alignment_summary.json"
    summary_md_path = figures_dir / "meeteval_cpwer_alignment_summary.md"

    with alignment_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=ALIGNMENT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    alignment_json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    alignment_md_path.write_text("\n".join(build_alignment_lines(rows)) + "\n", encoding="utf-8")
    with summary_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerow(summary_row)
    summary_json_path.write_text(json.dumps(summary_row, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_md_path.write_text("\n".join(build_alignment_summary_lines(summary_row)) + "\n", encoding="utf-8")
    return (
        alignment_csv_path,
        alignment_json_path,
        alignment_md_path,
        summary_csv_path,
        summary_json_path,
        summary_md_path,
    )


def main() -> None:
    bridge_rows = load_cpwer_bridge_rows()
    alignment_rows = [build_alignment_row(row) for row in bridge_rows]
    summary_row = build_alignment_summary_row(alignment_rows)
    (
        alignment_csv_path,
        alignment_json_path,
        alignment_md_path,
        summary_csv_path,
        summary_json_path,
        summary_md_path,
    ) = write_outputs(alignment_rows, summary_row)
    print(f"Wrote MeetEval cpWER alignment CSV: {alignment_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER alignment JSON: {alignment_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER alignment note: {alignment_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER alignment summary CSV: {summary_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER alignment summary JSON: {summary_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER alignment summary note: {summary_md_path.relative_to(PROJECT_ROOT)}")
    print(
        f"Alignment summary: matched={summary_row['matched_count']}/{summary_row['case_count']}, "
        f"average_gap={summary_row['average_alignment_gap']}"
    )


if __name__ == "__main__":
    main()
