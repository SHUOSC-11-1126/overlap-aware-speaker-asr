from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "queue_status",
    "ready_chain_count",
    "total_chain_count",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_completion_summary() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_execution_status_batch_completion_summary.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(summary: dict[str, str]) -> list[dict[str, str]]:
    queue_status = str(summary.get("queue_status", "queue_in_progress"))
    ready_count = str(summary.get("ready_chain_count", "0"))
    total_count = str(summary.get("total_chain_count", "0"))
    return [
        {
            "checklist_order": "1",
            "queue_status": queue_status,
            "ready_chain_count": ready_count,
            "total_chain_count": total_count,
            "prerequisite_artifact": "results/figures/meeteval_cpwer_execution_status_batch_completion_summary.md",
            "receipt_target": "results/tables/meeteval_cpwer_execution_status_batch_handoff.csv",
            "checklist_goal": (
                "Verify the batch execution-chain completion summary before opening the batch execution handoff."
            ),
            "bridge_note": (
                f"Completion summary reports queue_status={queue_status} with "
                f"{ready_count}/{total_count} cases execution_chain_ready; "
                "confirm batch readiness before advancing to official cpWER execution handoff."
            ),
            "next_gate": "Confirm this bridge before opening the MeetEval cpWER batch execution handoff.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Execution Status Batch Completion Summary Bridge Checklist",
        "",
        "This generated checklist connects the batch completion summary to the batch execution handoff. "
        "It does not claim official cpWER execution.",
        "",
        "| checklist_order | queue_status | ready_chain_count | total_chain_count | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['queue_status']} | {row['ready_chain_count']} | "
            f"{row['total_chain_count']} | {row['prerequisite_artifact']} | {row['receipt_target']} | "
            f"{row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_execution_status_batch_completion_summary_bridge_checklist.csv"
    json_path = tables_dir / "meeteval_cpwer_execution_status_batch_completion_summary_bridge_checklist.json"
    md_path = figures_dir / "meeteval_cpwer_execution_status_batch_completion_summary_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_completion_summary())
    if not rows:
        print("Completion summary not found; bridge checklist not written.")
        return
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote MeetEval cpWER execution status batch completion summary bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER execution status batch completion summary bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER execution status batch completion summary bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
