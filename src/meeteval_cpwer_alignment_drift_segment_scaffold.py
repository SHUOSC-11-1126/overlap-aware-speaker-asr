from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


SCAFFOLD_COLUMNS = [
    "case_id",
    "label",
    "scaffold_status",
    "hypothesis_source",
    "inspection_target",
    "expected_evidence",
    "scaffold_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "scaffold_scope",
    "case_id",
    "writeback_note",
]


def load_drift_handoff_row() -> dict[str, Any]:
    handoff_path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_alignment_drift_handoff.json"
    if not handoff_path.exists():
        return {}
    payload = json.loads(handoff_path.read_text(encoding="utf-8"))
    if isinstance(payload, list) and payload:
        return payload[0]
    return {}


def build_scaffold_row(handoff_row: dict[str, Any]) -> dict[str, str]:
    case_id = str(handoff_row.get("case_id", "HeavyOverlap"))
    return {
        "case_id": case_id,
        "label": "experimental/frontier",
        "scaffold_status": "scaffold_only",
        "hypothesis_source": "separated_whisper_cleaned",
        "inspection_target": (
            f"Segment-level cleaned separated hypothesis export for {case_id} before cpWER bridge reconciliation."
        ),
        "expected_evidence": "results/tables/meeteval_hypothesis_segments.jsonl",
        "scaffold_note": (
            "Segment inspection scaffold only; no segment-level reconciliation or cpWER execution has been performed."
        ),
    }


def build_scaffold_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# MeetEval cpWER Alignment Drift Segment Scaffold",
        "",
        "This generated scaffold records the segment-inspection plan for the drift handoff case. "
        "It does not claim cpWER execution or reconciled alignment.",
        "",
        "| case_id | label | scaffold_status | hypothesis_source | inspection_target | expected_evidence | scaffold_note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['case_id']} | {row['label']} | {row['scaffold_status']} | {row['hypothesis_source']} | "
            f"{row['inspection_target']} | {row['expected_evidence']} | {row['scaffold_note']} |"
        ),
    ]
    return lines


def build_scaffold_receipt_rows(scaffold_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "scaffold_documented",
            "scaffold_scope": "single_drift_case",
            "case_id": str(scaffold_row.get("case_id", "")),
            "writeback_note": (
                "Segment inspection scaffold documented; segment-level reconciliation remains pending."
            ),
        }
    ]


def build_scaffold_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Alignment Drift Segment Scaffold Receipt",
        "",
        "This receipt records the segment scaffold writeback. It does not claim cpWER execution.",
        "",
        "| execution_status | scaffold_scope | case_id | writeback_note |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['scaffold_scope']} | {row['case_id']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    scaffold_row: dict[str, str],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_alignment_drift_segment_scaffold.csv"
    json_path = tables_dir / "meeteval_cpwer_alignment_drift_segment_scaffold.json"
    md_path = figures_dir / "meeteval_cpwer_alignment_drift_segment_scaffold.md"
    receipt_json_path = tables_dir / "meeteval_cpwer_alignment_drift_segment_scaffold_receipt.json"
    receipt_md_path = figures_dir / "meeteval_cpwer_alignment_drift_segment_scaffold_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SCAFFOLD_COLUMNS)
        writer.writeheader()
        writer.writerow(scaffold_row)
    json_path.write_text(json.dumps(scaffold_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_scaffold_lines(scaffold_row)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_scaffold_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path, receipt_json_path, receipt_md_path


def main() -> None:
    handoff_row = load_drift_handoff_row()
    scaffold_row = build_scaffold_row(handoff_row)
    receipt_rows = build_scaffold_receipt_rows(scaffold_row)
    csv_path, json_path, md_path, receipt_json_path, receipt_md_path = write_outputs(
        scaffold_row,
        receipt_rows,
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment scaffold CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment scaffold JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment scaffold note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment scaffold receipt JSON: "
        f"{receipt_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment scaffold receipt note: "
        f"{receipt_md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
