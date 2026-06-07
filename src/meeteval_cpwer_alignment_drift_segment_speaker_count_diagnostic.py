from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic import count_segments_per_speaker
from .meeteval_dry_run import load_jsonl_segments


SPEAKER_COLUMNS = [
    "case_id",
    "speaker",
    "reference_segment_count",
    "hypothesis_segment_count",
    "segment_count_delta",
    "count_match",
]

SUMMARY_COLUMNS = [
    "case_id",
    "mismatched_speaker_count",
    "speaker_segment_count_match",
    "dominant_blocker",
    "diagnostic_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "diagnostic_scope",
    "case_id",
    "mismatched_speaker_count",
    "writeback_note",
]


def load_reconciliation_diagnostic() -> dict[str, Any]:
    diagnostic_path = (
        PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic.json"
    )
    if not diagnostic_path.exists():
        return {}
    payload = json.loads(diagnostic_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_speaker_rows(case_id: str, reference_counts: Counter[str], hypothesis_counts: Counter[str]) -> list[dict[str, str]]:
    speakers = sorted(set(reference_counts) | set(hypothesis_counts))
    rows: list[dict[str, str]] = []
    for speaker in speakers:
        reference_count = reference_counts.get(speaker, 0)
        hypothesis_count = hypothesis_counts.get(speaker, 0)
        delta = hypothesis_count - reference_count
        rows.append(
            {
                "case_id": case_id,
                "speaker": speaker,
                "reference_segment_count": str(reference_count),
                "hypothesis_segment_count": str(hypothesis_count),
                "segment_count_delta": str(delta),
                "count_match": str(reference_count == hypothesis_count),
            }
        )
    return rows


def build_summary_row(case_id: str, speaker_rows: list[dict[str, str]]) -> dict[str, str]:
    mismatched = [row for row in speaker_rows if row["count_match"] == "False"]
    mismatched_speaker_count = len(mismatched)
    speaker_segment_count_match = mismatched_speaker_count == 0
    if mismatched:
        dominant = max(mismatched, key=lambda row: abs(int(row["segment_count_delta"])))
        dominant_blocker = (
            f"{dominant['speaker']} delta={dominant['segment_count_delta']}"
        )
        diagnostic_note = (
            f"Per-speaker segment count drift detected for {case_id}; "
            f"mismatched_speaker_count={mismatched_speaker_count}. "
            "Reconciled alignment and cpWER execution remain pending."
        )
    else:
        dominant_blocker = "none"
        diagnostic_note = (
            f"Per-speaker segment counts align for {case_id}; "
            "reconciled alignment and cpWER execution remain pending."
        )
    return {
        "case_id": case_id,
        "mismatched_speaker_count": str(mismatched_speaker_count),
        "speaker_segment_count_match": str(speaker_segment_count_match),
        "dominant_blocker": dominant_blocker,
        "diagnostic_note": diagnostic_note,
    }


def build_speaker_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Alignment Drift Segment Speaker Count Diagnostic",
        "",
        "This generated note records per-speaker segment count comparison for the drift reconciliation case. "
        "It does not claim reconciled alignment or cpWER execution.",
        "",
        "| case_id | speaker | reference_segment_count | hypothesis_segment_count | segment_count_delta | count_match |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['speaker']} | {row['reference_segment_count']} | "
            f"{row['hypothesis_segment_count']} | {row['segment_count_delta']} | {row['count_match']} |"
        )
    return lines


def build_summary_lines(summary: dict[str, str]) -> list[str]:
    lines = [
        "# MeetEval cpWER Alignment Drift Segment Speaker Count Diagnostic Summary",
        "",
        "This generated summary condenses the per-speaker segment count drift for the reconciliation case. "
        "It does not claim reconciled alignment or cpWER execution.",
        "",
        "| case_id | mismatched_speaker_count | speaker_segment_count_match | dominant_blocker | diagnostic_note |",
        "| --- | ---: | --- | --- | --- |",
        (
            f"| {summary['case_id']} | {summary['mismatched_speaker_count']} | "
            f"{summary['speaker_segment_count_match']} | {summary['dominant_blocker']} | {summary['diagnostic_note']} |"
        ),
    ]
    return lines


def build_receipt_row(summary: dict[str, str]) -> dict[str, str]:
    return {
        "execution_status": "speaker_count_diagnostic_complete",
        "diagnostic_scope": "single_drift_case_per_speaker",
        "case_id": str(summary.get("case_id", "")),
        "mismatched_speaker_count": str(summary.get("mismatched_speaker_count", "0")),
        "writeback_note": (
            "Per-speaker segment count diagnostic complete for the drift case. "
            "Reconciled alignment and cpWER execution remain pending."
        ),
    }


def build_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Alignment Drift Segment Speaker Count Diagnostic Receipt",
        "",
        "This receipt records the per-speaker count diagnostic writeback. "
        "It does not claim reconciled alignment or cpWER execution.",
        "",
        "| execution_status | diagnostic_scope | case_id | mismatched_speaker_count | writeback_note |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['diagnostic_scope']} | {row['case_id']} | "
            f"{row['mismatched_speaker_count']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    speaker_rows: list[dict[str, str]],
    summary: dict[str, str],
    receipt_row: dict[str, str],
) -> tuple[Path, Path, Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    speaker_csv_path = tables_dir / "meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic.csv"
    speaker_json_path = tables_dir / "meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic.json"
    speaker_md_path = figures_dir / "meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic.md"
    summary_csv_path = tables_dir / "meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_summary.csv"
    summary_json_path = tables_dir / "meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_summary.json"
    summary_md_path = figures_dir / "meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_summary.md"
    receipt_json_path = tables_dir / "meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_receipt.json"
    receipt_md_path = figures_dir / "meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_receipt.md"

    with speaker_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SPEAKER_COLUMNS)
        writer.writeheader()
        writer.writerows(speaker_rows)
    speaker_json_path.write_text(json.dumps(speaker_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    speaker_md_path.write_text("\n".join(build_speaker_lines(speaker_rows)) + "\n", encoding="utf-8")

    with summary_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerow(summary)
    summary_json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_md_path.write_text("\n".join(build_summary_lines(summary)) + "\n", encoding="utf-8")

    receipt_json_path.write_text(json.dumps([receipt_row], ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_receipt_lines([receipt_row])) + "\n", encoding="utf-8")
    return (
        speaker_csv_path,
        speaker_json_path,
        speaker_md_path,
        summary_csv_path,
        summary_json_path,
        summary_md_path,
        receipt_json_path,
        receipt_md_path,
    )


def run_speaker_count_diagnostic(case_id: str) -> tuple[list[dict[str, str]], dict[str, str]]:
    reference_path = PROJECT_ROOT / "results" / "tables" / "meeteval_reference_segments.jsonl"
    hypothesis_path = PROJECT_ROOT / "results" / "tables" / "meeteval_hypothesis_segments.jsonl"
    reference_segments = load_jsonl_segments(reference_path, case_id)
    hypothesis_segments = load_jsonl_segments(hypothesis_path, case_id)
    speaker_rows = build_speaker_rows(
        case_id,
        count_segments_per_speaker(reference_segments),
        count_segments_per_speaker(hypothesis_segments),
    )
    summary = build_summary_row(case_id, speaker_rows)
    return speaker_rows, summary


def main() -> None:
    diagnostic = load_reconciliation_diagnostic()
    case_id = str(diagnostic.get("case_id", "HeavyOverlap"))
    speaker_rows, summary = run_speaker_count_diagnostic(case_id)
    receipt_row = build_receipt_row(summary)
    (
        speaker_csv_path,
        speaker_json_path,
        speaker_md_path,
        summary_csv_path,
        summary_json_path,
        summary_md_path,
        receipt_json_path,
        receipt_md_path,
    ) = write_outputs(speaker_rows, summary, receipt_row)
    print(
        "Wrote MeetEval cpWER alignment drift segment speaker count diagnostic CSV: "
        f"{speaker_csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment speaker count diagnostic JSON: "
        f"{speaker_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment speaker count diagnostic note: "
        f"{speaker_md_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment speaker count diagnostic summary CSV: "
        f"{summary_csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment speaker count diagnostic summary JSON: "
        f"{summary_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment speaker count diagnostic summary note: "
        f"{summary_md_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment speaker count diagnostic receipt JSON: "
        f"{receipt_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment speaker count diagnostic receipt note: "
        f"{receipt_md_path.relative_to(PROJECT_ROOT)}"
    )
    print(f"Mismatched speaker count: {summary['mismatched_speaker_count']}")


if __name__ == "__main__":
    main()
