from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "case_id",
    "execution_chain_status",
    "preflight_pass",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_status_row() -> dict[str, str]:
    status_path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_execution_status.json"
    if not status_path.exists():
        return {}
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(status_row: dict[str, str]) -> list[dict[str, str]]:
    case_id = str(status_row.get("case_id", "NoOverlap"))
    chain_status = str(status_row.get("execution_chain_status", "execution_chain_in_progress"))
    preflight_pass = str(status_row.get("preflight_pass", ""))
    return [
        {
            "checklist_order": "1",
            "case_id": case_id,
            "execution_chain_status": chain_status,
            "preflight_pass": preflight_pass,
            "prerequisite_artifact": "results/figures/meeteval_cpwer_execution_status.md",
            "receipt_target": "results/tables/meeteval_cpwer_execution_receipt.json",
            "checklist_goal": (
                f"Verify the cpWER execution-chain status rollup for {case_id} before any official MeetEval run."
            ),
            "bridge_note": (
                f"Status rollup reports execution_chain_status={chain_status} with preflight_pass={preflight_pass}; "
                "confirm chain readiness before filling the official cpWER execution receipt."
            ),
            "next_gate": "Confirm this bridge before claiming any official MeetEval cpWER evaluation.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Execution Status Bridge Checklist",
        "",
        "This generated checklist turns the cpWER execution-chain status rollup into a row-by-row bridge verification path. "
        "It remains experimental/frontier coordination only and does not claim official cpWER execution.",
        "",
        "| checklist_order | case_id | execution_chain_status | preflight_pass | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['case_id']} | {row['execution_chain_status']} | {row['preflight_pass']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_execution_status_bridge_checklist.csv"
    json_path = tables_dir / "meeteval_cpwer_execution_status_bridge_checklist.json"
    md_path = figures_dir / "meeteval_cpwer_execution_status_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    status_row = load_status_row()
    rows = build_bridge_checklist_rows(status_row)
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote MeetEval cpWER execution status bridge checklist CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution status bridge checklist JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution status bridge checklist note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
