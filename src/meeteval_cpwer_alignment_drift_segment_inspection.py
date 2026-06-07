from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .export_meeteval_compatibility import load_hypothesis_payload
from .meeteval_dry_run import (
    extract_speakers,
    load_jsonl_segments,
    time_ranges_valid,
)


INSPECTION_COLUMNS = [
    "case_id",
    "hypothesis_source",
    "reference_segment_count",
    "hypothesis_segment_count",
    "segment_count_delta",
    "speaker_set_match",
    "time_range_valid",
    "export_path_valid",
    "inspection_pass",
    "inspection_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "inspection_scope",
    "case_id",
    "hypothesis_source",
    "reference_segment_count",
    "hypothesis_segment_count",
    "segment_count_delta",
    "inspection_pass",
    "writeback_note",
]


def load_segment_handoff_row() -> dict[str, Any]:
    handoff_path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_alignment_drift_segment_handoff.json"
    if not handoff_path.exists():
        return {}
    payload = json.loads(handoff_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def run_segment_inspection(case_id: str) -> dict[str, Any]:
    reference_path = PROJECT_ROOT / "results" / "tables" / "meeteval_reference_segments.jsonl"
    hypothesis_path = PROJECT_ROOT / "results" / "tables" / "meeteval_hypothesis_segments.jsonl"
    reference_segments = load_jsonl_segments(reference_path, case_id)
    hypothesis_segments = load_jsonl_segments(hypothesis_path, case_id)
    reference_count = len(reference_segments)
    hypothesis_count = len(hypothesis_segments)
    segment_count_delta = hypothesis_count - reference_count
    export_path_valid = bool(reference_segments and hypothesis_segments)
    speaker_set_match = extract_speakers(reference_segments) == extract_speakers(hypothesis_segments)
    time_range_valid = time_ranges_valid(reference_segments) and time_ranges_valid(hypothesis_segments)
    inspection_pass = export_path_valid and speaker_set_match and time_range_valid

    hypothesis_source = ""
    try:
        hypothesis_source = str(load_hypothesis_payload(case_id).get("hypothesis_source", ""))
    except FileNotFoundError:
        hypothesis_source = "unknown"

    if inspection_pass:
        inspection_note = (
            f"Segment export path validated for drift case {case_id}; "
            f"segment_count_delta={segment_count_delta}. "
            "Segment reconciliation and cpWER execution remain pending."
        )
    else:
        inspection_note = (
            f"Segment export path check for drift case {case_id} found issues; "
            "review segment exports before any reconciliation or cpWER claim."
        )

    return {
        "case_id": case_id,
        "hypothesis_source": hypothesis_source,
        "reference_segment_count": reference_count,
        "hypothesis_segment_count": hypothesis_count,
        "segment_count_delta": segment_count_delta,
        "speaker_set_match": speaker_set_match,
        "time_range_valid": time_range_valid,
        "export_path_valid": export_path_valid,
        "inspection_pass": inspection_pass,
        "inspection_note": inspection_note,
    }


def build_inspection_receipt_row(inspection: dict[str, Any]) -> dict[str, str]:
    return {
        "execution_status": "segment_inspection_complete",
        "inspection_scope": "single_drift_case",
        "case_id": str(inspection.get("case_id", "")),
        "hypothesis_source": str(inspection.get("hypothesis_source", "")),
        "reference_segment_count": str(inspection.get("reference_segment_count", 0)),
        "hypothesis_segment_count": str(inspection.get("hypothesis_segment_count", 0)),
        "segment_count_delta": str(inspection.get("segment_count_delta", 0)),
        "inspection_pass": str(inspection.get("inspection_pass", False)),
        "writeback_note": (
            "Narrow segment inspection complete for the drift case. "
            "Segment reconciliation and cpWER execution remain pending."
        ),
    }


def build_inspection_summary_lines(inspection: dict[str, Any]) -> list[str]:
    lines = [
        "# MeetEval cpWER Alignment Drift Segment Inspection",
        "",
        "This generated note records the first narrow segment inspection for the drift handoff case. "
        "It does not claim segment reconciliation or cpWER execution.",
        "",
        "| case_id | hypothesis_source | reference_segment_count | hypothesis_segment_count | segment_count_delta | speaker_set_match | time_range_valid | export_path_valid | inspection_pass | inspection_note |",
        "| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- | --- |",
        (
            f"| {inspection['case_id']} | {inspection['hypothesis_source']} | "
            f"{inspection['reference_segment_count']} | {inspection['hypothesis_segment_count']} | "
            f"{inspection['segment_count_delta']} | {inspection['speaker_set_match']} | "
            f"{inspection['time_range_valid']} | {inspection['export_path_valid']} | "
            f"{inspection['inspection_pass']} | {inspection['inspection_note']} |"
        ),
    ]
    return lines


def build_inspection_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Alignment Drift Segment Inspection Receipt",
        "",
        "This receipt records the narrow segment inspection writeback. "
        "It does not claim segment reconciliation or cpWER execution.",
        "",
        "| execution_status | inspection_scope | case_id | hypothesis_source | reference_segment_count | hypothesis_segment_count | segment_count_delta | inspection_pass | writeback_note |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['inspection_scope']} | {row['case_id']} | "
            f"{row['hypothesis_source']} | {row['reference_segment_count']} | "
            f"{row['hypothesis_segment_count']} | {row['segment_count_delta']} | "
            f"{row['inspection_pass']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    inspection: dict[str, Any],
    receipt_row: dict[str, str],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_alignment_drift_segment_inspection.csv"
    json_path = tables_dir / "meeteval_cpwer_alignment_drift_segment_inspection.json"
    md_path = figures_dir / "meeteval_cpwer_alignment_drift_segment_inspection.md"
    receipt_json_path = tables_dir / "meeteval_cpwer_alignment_drift_segment_inspection_receipt.json"
    receipt_md_path = figures_dir / "meeteval_cpwer_alignment_drift_segment_inspection_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=INSPECTION_COLUMNS)
        writer.writeheader()
        writer.writerow(inspection)
    json_path.write_text(json.dumps(inspection, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_inspection_summary_lines(inspection)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps([receipt_row], ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_inspection_receipt_lines([receipt_row])) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path, receipt_json_path, receipt_md_path


def main() -> None:
    handoff_row = load_segment_handoff_row()
    case_id = str(handoff_row.get("case_id", "HeavyOverlap"))
    inspection = run_segment_inspection(case_id)
    receipt_row = build_inspection_receipt_row(inspection)
    csv_path, json_path, md_path, receipt_json_path, receipt_md_path = write_outputs(
        inspection,
        receipt_row,
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment inspection CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment inspection JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment inspection note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment inspection receipt JSON: "
        f"{receipt_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment inspection receipt note: "
        f"{receipt_md_path.relative_to(PROJECT_ROOT)}"
    )
    print(f"Inspection pass: {inspection['inspection_pass']}")


if __name__ == "__main__":
    main()
