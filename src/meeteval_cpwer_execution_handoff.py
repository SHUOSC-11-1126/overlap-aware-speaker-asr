from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


HANDOFF_COLUMNS = [
    "handoff_status",
    "case_id",
    "scaffold_status",
    "cpwer_bridge_lite",
    "execution_target",
    "handoff_goal",
    "expected_evidence",
    "handoff_note",
]


def load_execution_scaffold() -> dict[str, Any]:
    scaffold_path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_execution_scaffold.json"
    if not scaffold_path.exists():
        return {}
    payload = json.loads(scaffold_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_handoff_row(scaffold: dict[str, Any]) -> dict[str, str]:
    case_id = str(scaffold.get("case_id", "NoOverlap"))
    scaffold_status = str(scaffold.get("scaffold_status", "scaffold_only"))
    cpwer_value = str(scaffold.get("cpwer_bridge_lite", ""))
    return {
        "handoff_status": "execution_handoff_ready",
        "case_id": case_id,
        "scaffold_status": scaffold_status,
        "cpwer_bridge_lite": cpwer_value,
        "execution_target": "results/tables/meeteval_cpwer_execution_receipt.json",
        "handoff_goal": (
            f"Run a narrow official MeetEval cpWER evaluation for {case_id} after the execution scaffold audit."
        ),
        "expected_evidence": "results/tables/meeteval_cpwer_execution_receipt.json",
        "handoff_note": (
            "experimental/frontier cpWER execution handoff only; official benchmark completion is not claimed."
        ),
    }


def build_handoff_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# MeetEval cpWER Execution Handoff",
        "",
        "This generated handoff turns the cpWER execution scaffold into the next narrow MeetEval frontier step. "
        "It does not claim official cpWER evaluation or benchmark completion.",
        "",
        "| handoff_status | case_id | scaffold_status | cpwer_bridge_lite | execution_target | handoff_goal | expected_evidence | handoff_note |",
        "| --- | --- | --- | ---: | --- | --- | --- | --- |",
        (
            f"| {row['handoff_status']} | {row['case_id']} | {row['scaffold_status']} | {row['cpwer_bridge_lite']} | "
            f"{row['execution_target']} | {row['handoff_goal']} | {row['expected_evidence']} | {row['handoff_note']} |"
        ),
    ]
    return lines


def build_handoff_receipt_rows(handoff_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "handoff_documented",
            "handoff_scope": "single_case_cpwer_execution",
            "case_id": str(handoff_row.get("case_id", "")),
            "writeback_note": (
                "cpWER execution handoff documented for coordination; "
                "official MeetEval evaluation remains pending."
            ),
        }
    ]


def build_handoff_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Execution Handoff Receipt",
        "",
        "This receipt records the cpWER execution handoff writeback. It does not claim cpWER execution.",
        "",
        "| execution_status | handoff_scope | case_id | writeback_note |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['handoff_scope']} | {row['case_id']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    handoff_row: dict[str, str],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_execution_handoff.csv"
    json_path = tables_dir / "meeteval_cpwer_execution_handoff.json"
    md_path = figures_dir / "meeteval_cpwer_execution_handoff.md"
    receipt_json_path = tables_dir / "meeteval_cpwer_execution_handoff_receipt.json"
    receipt_md_path = figures_dir / "meeteval_cpwer_execution_handoff_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HANDOFF_COLUMNS)
        writer.writeheader()
        writer.writerow(handoff_row)
    json_path.write_text(json.dumps(handoff_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_handoff_lines(handoff_row)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_handoff_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path, receipt_json_path, receipt_md_path


def main() -> None:
    scaffold = load_execution_scaffold()
    handoff_row = build_handoff_row(scaffold)
    receipt_rows = build_handoff_receipt_rows(handoff_row)
    csv_path, json_path, md_path, receipt_json_path, receipt_md_path = write_outputs(
        handoff_row,
        receipt_rows,
    )
    print(f"Wrote MeetEval cpWER execution handoff CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution handoff JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution handoff note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution handoff receipt JSON: {receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution handoff receipt note: {receipt_md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
