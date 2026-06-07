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
    "inspection_status",
    "reconciliation_target",
    "expected_evidence",
    "scaffold_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "scaffold_scope",
    "case_id",
    "writeback_note",
]


def load_segment_inspection() -> dict[str, Any]:
    inspection_path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_alignment_drift_segment_inspection.json"
    if not inspection_path.exists():
        return {}
    payload = json.loads(inspection_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_scaffold_row(inspection: dict[str, Any]) -> dict[str, str]:
    case_id = str(inspection.get("case_id", "HeavyOverlap"))
    inspection_pass = inspection.get("inspection_pass", False)
    passed = inspection_pass if isinstance(inspection_pass, bool) else str(inspection_pass).lower() == "true"
    inspection_status = "segment_inspection_complete" if passed else "segment_inspection_pending"
    return {
        "case_id": case_id,
        "label": "experimental/frontier",
        "scaffold_status": "scaffold_only",
        "inspection_status": inspection_status,
        "reconciliation_target": (
            f"Speaker-attributed segment reconciliation for {case_id} before any cpWER bridge advance."
        ),
        "expected_evidence": "results/tables/meeteval_hypothesis_segments.jsonl",
        "scaffold_note": (
            "Segment reconciliation scaffold only; no reconciled alignment or cpWER execution has been performed."
        ),
    }


def build_scaffold_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# MeetEval cpWER Alignment Drift Segment Reconciliation Scaffold",
        "",
        "This generated scaffold records the reconciliation plan after the narrow segment inspection. "
        "It does not claim reconciled alignment or cpWER execution.",
        "",
        "| case_id | label | scaffold_status | inspection_status | reconciliation_target | expected_evidence | scaffold_note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['case_id']} | {row['label']} | {row['scaffold_status']} | {row['inspection_status']} | "
            f"{row['reconciliation_target']} | {row['expected_evidence']} | {row['scaffold_note']} |"
        ),
    ]
    return lines


def build_scaffold_receipt_rows(scaffold_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "scaffold_documented",
            "scaffold_scope": "single_drift_case_reconciliation",
            "case_id": str(scaffold_row.get("case_id", "")),
            "writeback_note": (
                "Segment reconciliation scaffold documented; reconciled alignment and cpWER execution remain pending."
            ),
        }
    ]


def build_scaffold_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Alignment Drift Segment Reconciliation Scaffold Receipt",
        "",
        "This receipt records the reconciliation scaffold writeback. It does not claim cpWER execution.",
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

    csv_path = tables_dir / "meeteval_cpwer_alignment_drift_segment_reconciliation_scaffold.csv"
    json_path = tables_dir / "meeteval_cpwer_alignment_drift_segment_reconciliation_scaffold.json"
    md_path = figures_dir / "meeteval_cpwer_alignment_drift_segment_reconciliation_scaffold.md"
    receipt_json_path = tables_dir / "meeteval_cpwer_alignment_drift_segment_reconciliation_scaffold_receipt.json"
    receipt_md_path = figures_dir / "meeteval_cpwer_alignment_drift_segment_reconciliation_scaffold_receipt.md"

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
    inspection = load_segment_inspection()
    scaffold_row = build_scaffold_row(inspection)
    receipt_rows = build_scaffold_receipt_rows(scaffold_row)
    csv_path, json_path, md_path, receipt_json_path, receipt_md_path = write_outputs(
        scaffold_row,
        receipt_rows,
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment reconciliation scaffold CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment reconciliation scaffold JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment reconciliation scaffold note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment reconciliation scaffold receipt JSON: "
        f"{receipt_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift segment reconciliation scaffold receipt note: "
        f"{receipt_md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
