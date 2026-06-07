from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


SCAFFOLD_COLUMNS = [
    "case_id",
    "bridge_status",
    "cpwer_bridge_lite",
    "scaffold_status",
    "expected_inputs",
    "expected_outputs",
    "scaffold_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "scaffold_scope",
    "case_id",
    "writeback_note",
]


def load_cpwer_bridge_handoff() -> dict[str, Any]:
    handoff_path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_bridge_handoff.json"
    if not handoff_path.exists():
        return {}
    payload = json.loads(handoff_path.read_text(encoding="utf-8"))
    if isinstance(payload, list) and payload:
        first = payload[0]
        return first if isinstance(first, dict) else {}
    return payload if isinstance(payload, dict) else {}


def build_scaffold_row(handoff: dict[str, Any]) -> dict[str, str]:
    case_id = str(handoff.get("case_id", "NoOverlap"))
    bridge_status = str(handoff.get("bridge_status", "cpwer_bridge_complete"))
    cpwer_value = str(handoff.get("cpwer_bridge_lite", ""))
    return {
        "case_id": case_id,
        "bridge_status": bridge_status,
        "cpwer_bridge_lite": cpwer_value,
        "scaffold_status": "scaffold_only",
        "expected_inputs": (
            "results/tables/meeteval_reference_segments.jsonl; "
            "results/tables/meeteval_hypothesis_segments.jsonl; MeetEval cpWER tooling."
        ),
        "expected_outputs": "Official cpWER score receipt for one verified gold case.",
        "scaffold_note": (
            f"Template-only full MeetEval cpWER execution scaffold for {case_id}. "
            "Bridge-lite context is recorded; official cpWER execution remains pending."
        ),
    }


def build_scaffold_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# MeetEval cpWER Execution Scaffold",
        "",
        "This generated note records a template-only full MeetEval cpWER execution scaffold. "
        "It does not claim official cpWER evaluation or benchmark completion.",
        "",
        "| case_id | bridge_status | cpwer_bridge_lite | scaffold_status | expected_inputs | expected_outputs | scaffold_note |",
        "| --- | --- | ---: | --- | --- | --- | --- |",
        (
            f"| {row['case_id']} | {row['bridge_status']} | {row['cpwer_bridge_lite']} | {row['scaffold_status']} | "
            f"{row['expected_inputs']} | {row['expected_outputs']} | {row['scaffold_note']} |"
        ),
    ]
    return lines


def build_scaffold_receipt_rows(scaffold_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "scaffold_complete",
            "scaffold_scope": "single_verified_case_cpwer_execution",
            "case_id": str(scaffold_row.get("case_id", "")),
            "writeback_note": (
                "Full MeetEval cpWER execution scaffold documented; "
                "official cpWER evaluation remains pending."
            ),
        }
    ]


def build_scaffold_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Execution Scaffold Receipt",
        "",
        "This receipt records the cpWER execution scaffold writeback. It does not claim cpWER execution.",
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

    csv_path = tables_dir / "meeteval_cpwer_execution_scaffold.csv"
    json_path = tables_dir / "meeteval_cpwer_execution_scaffold.json"
    md_path = figures_dir / "meeteval_cpwer_execution_scaffold.md"
    receipt_json_path = tables_dir / "meeteval_cpwer_execution_scaffold_receipt.json"
    receipt_md_path = figures_dir / "meeteval_cpwer_execution_scaffold_receipt.md"

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
    handoff = load_cpwer_bridge_handoff()
    scaffold_row = build_scaffold_row(handoff)
    receipt_rows = build_scaffold_receipt_rows(scaffold_row)
    csv_path, json_path, md_path, receipt_json_path, receipt_md_path = write_outputs(
        scaffold_row,
        receipt_rows,
    )
    print(f"Wrote MeetEval cpWER execution scaffold CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution scaffold JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution scaffold note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution scaffold receipt JSON: {receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution scaffold receipt note: {receipt_md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
