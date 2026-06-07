from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "execution_chain_ready_count",
    "execution_chain_total_count",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_status_batch_rows() -> list[dict[str, str]]:
    path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_execution_status_batch.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_bridge_checklist_rows(status_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not status_rows:
        return []
    ready_count = sum(1 for row in status_rows if row.get("execution_chain_status") == "execution_chain_ready")
    total_count = str(len(status_rows))
    return [
        {
            "checklist_order": "1",
            "execution_chain_ready_count": str(ready_count),
            "execution_chain_total_count": total_count,
            "prerequisite_artifact": "results/figures/meeteval_cpwer_execution_status_batch.md",
            "receipt_target": "results/tables/meeteval_cpwer_execution_receipt.json",
            "checklist_goal": (
                "Verify the batch execution chain status before opening the official cpWER execution receipt."
            ),
            "bridge_note": (
                f"Batch status reports {ready_count}/{total_count} cases execution_chain_ready; "
                "confirm preflight and scaffold alignment before official cpWER execution."
            ),
            "next_gate": "Confirm this bridge before opening the official MeetEval cpWER execution receipt.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Execution Status Batch Bridge Checklist",
        "",
        "This generated checklist connects the batch execution chain status to the official execution receipt target. "
        "It does not claim cpWER execution.",
        "",
        "| checklist_order | execution_chain_ready_count | execution_chain_total_count | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['execution_chain_ready_count']} | {row['execution_chain_total_count']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_execution_status_batch_bridge_checklist.csv"
    json_path = tables_dir / "meeteval_cpwer_execution_status_batch_bridge_checklist.json"
    md_path = figures_dir / "meeteval_cpwer_execution_status_batch_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_status_batch_rows())
    if not rows:
        print("Status batch not found; bridge checklist not written.")
        return
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote MeetEval cpWER execution status batch bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER execution status batch bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER execution status batch bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
