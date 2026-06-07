from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .meeteval_cpwer_execution_preflight_batch import GOLD_CASES


STATUS_COLUMNS = [
    "scope",
    "case_id",
    "preflight_pass",
    "receipt_scaffold_status",
    "execution_receipt_status",
    "execution_chain_status",
    "status_note",
]


def load_json_list(path_rel: str) -> list[dict[str, Any]]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def load_receipt_template_status(path_rel: str) -> str:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return "missing"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            return str(first.get("execution_status", "unknown"))
    return "unknown"


def build_status_row(
    preflight: dict[str, Any],
    receipt_scaffold: dict[str, Any],
    execution_receipt_status: str,
) -> dict[str, str]:
    case_id = str(preflight.get("case_id", receipt_scaffold.get("case_id", "NoOverlap")))
    preflight_pass = bool(preflight.get("preflight_pass", False))
    scaffold_status = str(receipt_scaffold.get("scaffold_status", "missing"))
    chain_ready = preflight_pass and scaffold_status == "receipt_batch_scaffold_only"
    chain_status = "execution_chain_ready" if chain_ready else "execution_chain_in_progress"
    return {
        "scope": "meeteval_cpwer_execution_chain_batch",
        "case_id": case_id,
        "preflight_pass": str(preflight_pass),
        "receipt_scaffold_status": scaffold_status,
        "execution_receipt_status": execution_receipt_status,
        "execution_chain_status": chain_status,
        "status_note": (
            "experimental/frontier batch execution-chain rollup for one verified gold case; "
            "official MeetEval cpWER evaluation is not claimed."
        ),
    }


def build_status_rows(
    preflight_rows: list[dict[str, Any]],
    scaffold_rows: list[dict[str, Any]],
    execution_receipt_status: str,
) -> list[dict[str, str]]:
    scaffold_by_case = {str(row.get("case_id", "")): row for row in scaffold_rows}
    if preflight_rows:
        source_rows = preflight_rows
    else:
        source_rows = [{"case_id": case_id} for case_id in GOLD_CASES]
    return [
        build_status_row(
            preflight,
            scaffold_by_case.get(str(preflight.get("case_id", "")), {}),
            execution_receipt_status,
        )
        for preflight in source_rows
    ]


def build_status_lines(rows: list[dict[str, str]]) -> list[str]:
    ready_count = sum(1 for row in rows if row.get("execution_chain_status") == "execution_chain_ready")
    lines = [
        "# MeetEval cpWER Execution Status Batch",
        "",
        "This generated note rolls up the cpWER execution chain status across all five verified gold cases. "
        "It does not claim official MeetEval evaluation or benchmark completion.",
        "",
        f"Summary: `{ready_count}/{len(rows)}` cases report execution_chain_ready.",
        "",
        "| scope | case_id | preflight_pass | receipt_scaffold_status | execution_receipt_status | execution_chain_status | status_note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['scope']} | {row['case_id']} | {row['preflight_pass']} | {row['receipt_scaffold_status']} | "
            f"{row['execution_receipt_status']} | {row['execution_chain_status']} | {row['status_note']} |"
        )
    return lines


def write_outputs(status_rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_execution_status_batch.csv"
    json_path = tables_dir / "meeteval_cpwer_execution_status_batch.json"
    md_path = figures_dir / "meeteval_cpwer_execution_status_batch.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=STATUS_COLUMNS)
        writer.writeheader()
        writer.writerows(status_rows)
    json_path.write_text(json.dumps(status_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_status_lines(status_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    preflight_rows = load_json_list("results/tables/meeteval_cpwer_execution_preflight_batch.json")
    scaffold_rows = load_json_list("results/tables/meeteval_cpwer_execution_receipt_batch_scaffold.json")
    execution_receipt_status = load_receipt_template_status("results/tables/meeteval_cpwer_execution_receipt.json")
    status_rows = build_status_rows(preflight_rows, scaffold_rows, execution_receipt_status)
    csv_path, json_path, md_path = write_outputs(status_rows)
    ready_count = sum(1 for row in status_rows if row.get("execution_chain_status") == "execution_chain_ready")
    print(f"Wrote MeetEval cpWER execution status batch CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution status batch JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution status batch note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Execution chain ready: {ready_count}/{len(status_rows)}")


if __name__ == "__main__":
    main()
