from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .meeteval_cpwer_execution_preflight_batch import GOLD_CASES
from .meeteval_dry_run import select_preferred_case


HANDOFF_COLUMNS = [
    "handoff_order",
    "handoff_status",
    "case_id",
    "execution_chain_status",
    "hypothesis_source",
    "execution_target",
    "handoff_goal",
    "expected_evidence",
    "handoff_note",
]


def load_json_list(path_rel: str) -> list[dict[str, Any]]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def resolve_first_case_id(status_rows: list[dict[str, Any]]) -> str:
    for row in status_rows:
        if row.get("execution_chain_status") == "execution_chain_ready":
            return str(row.get("case_id", "NoOverlap"))
    checklist_path = PROJECT_ROOT / "results" / "tables" / "meeteval_dry_run_checklist.csv"
    return select_preferred_case(checklist_path)


def build_handoff_rows(
    status_rows: list[dict[str, Any]],
    preflight_rows: list[dict[str, Any]],
) -> list[dict[str, str]]:
    preflight_by_case = {str(row.get("case_id", "")): row for row in preflight_rows}
    if status_rows:
        source_rows = status_rows
    else:
        source_rows = [{"case_id": case_id} for case_id in GOLD_CASES]

    first_case = resolve_first_case_id(source_rows)
    handoff_rows: list[dict[str, str]] = []
    for order, status in enumerate(source_rows, start=1):
        case_id = str(status.get("case_id", ""))
        chain_status = str(status.get("execution_chain_status", "execution_chain_in_progress"))
        preflight = preflight_by_case.get(case_id, {})
        hypothesis_source = str(preflight.get("hypothesis_source", ""))
        is_first = case_id == first_case and chain_status == "execution_chain_ready"
        handoff_rows.append(
            {
                "handoff_order": str(order),
                "handoff_status": "execution_handoff_ready" if is_first else "execution_handoff_queued",
                "case_id": case_id,
                "execution_chain_status": chain_status,
                "hypothesis_source": hypothesis_source,
                "execution_target": "results/tables/meeteval_cpwer_execution_receipt.json",
                "handoff_goal": (
                    f"Run official MeetEval cpWER narrow dry run for {case_id} after batch chain readiness audit."
                    if is_first
                    else f"Queue official MeetEval cpWER execution for {case_id} after the first narrow dry run."
                ),
                "expected_evidence": "results/tables/meeteval_cpwer_execution_receipt.json",
                "handoff_note": (
                    "experimental/frontier batch cpWER execution handoff only; "
                    "official benchmark completion is not claimed."
                ),
            }
        )
    return handoff_rows


def build_handoff_lines(rows: list[dict[str, str]]) -> list[str]:
    ready_count = sum(1 for row in rows if row.get("execution_chain_status") == "execution_chain_ready")
    lines = [
        "# MeetEval cpWER Execution Status Batch Handoff",
        "",
        "This generated handoff turns the batch execution-chain status into per-case official cpWER execution actions. "
        "It does not claim official cpWER evaluation or benchmark completion.",
        "",
        f"Summary: `{ready_count}/{len(rows)}` cases are execution_chain_ready; first action targets the preferred ready case.",
        "",
        "| handoff_order | handoff_status | case_id | execution_chain_status | hypothesis_source | execution_target | handoff_goal | expected_evidence | handoff_note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['handoff_order']} | {row['handoff_status']} | {row['case_id']} | "
            f"{row['execution_chain_status']} | {row['hypothesis_source']} | {row['execution_target']} | "
            f"{row['handoff_goal']} | {row['expected_evidence']} | {row['handoff_note']} |"
        )
    return lines


def build_handoff_receipt_rows(handoff_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    first_ready = next(
        (row for row in handoff_rows if row.get("handoff_status") == "execution_handoff_ready"),
        handoff_rows[0] if handoff_rows else {},
    )
    return [
        {
            "execution_status": "batch_handoff_documented",
            "handoff_scope": "all_gold_cpwer_execution",
            "case_id": str(first_ready.get("case_id", "NoOverlap")),
            "writeback_note": (
                "Batch cpWER execution handoff documented for coordination; "
                "official MeetEval evaluation remains pending until receipt fill."
            ),
        }
    ]


def build_handoff_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Execution Status Batch Handoff Receipt",
        "",
        "This receipt records the batch execution handoff writeback. It does not claim cpWER execution.",
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
    handoff_rows: list[dict[str, str]],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_execution_status_batch_handoff.csv"
    json_path = tables_dir / "meeteval_cpwer_execution_status_batch_handoff.json"
    md_path = figures_dir / "meeteval_cpwer_execution_status_batch_handoff.md"
    receipt_json_path = tables_dir / "meeteval_cpwer_execution_status_batch_handoff_receipt.json"
    receipt_md_path = figures_dir / "meeteval_cpwer_execution_status_batch_handoff_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HANDOFF_COLUMNS)
        writer.writeheader()
        writer.writerows(handoff_rows)
    json_path.write_text(json.dumps(handoff_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_handoff_lines(handoff_rows)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_handoff_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path, receipt_json_path, receipt_md_path


def main() -> None:
    status_rows = load_json_list("results/tables/meeteval_cpwer_execution_status_batch.json")
    preflight_rows = load_json_list("results/tables/meeteval_cpwer_execution_preflight_batch.json")
    handoff_rows = build_handoff_rows(status_rows, preflight_rows)
    receipt_rows = build_handoff_receipt_rows(handoff_rows)
    csv_path, json_path, md_path, receipt_json_path, receipt_md_path = write_outputs(handoff_rows, receipt_rows)
    print(f"Wrote MeetEval cpWER execution status batch handoff CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution status batch handoff JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution status batch handoff note: {md_path.relative_to(PROJECT_ROOT)}")
    print(
        "Wrote MeetEval cpWER execution status batch handoff receipt JSON: "
        f"{receipt_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER execution status batch handoff receipt note: "
        f"{receipt_md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
