from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "queue_status",
    "complete_handoff_count",
    "total_handoff_count",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_completion_summary() -> dict[str, str]:
    path = (
        PROJECT_ROOT
        / "results"
        / "tables"
        / "meeteval_cpwer_execution_status_batch_handoff_completion_summary.json"
    )
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(summary: dict[str, str]) -> list[dict[str, str]]:
    if not summary:
        return []
    queue_status = str(summary.get("queue_status", "queue_in_progress"))
    complete_handoff_count = str(summary.get("complete_handoff_count", "0"))
    total_handoff_count = str(summary.get("total_handoff_count", "0"))
    return [
        {
            "checklist_order": "1",
            "queue_status": queue_status,
            "complete_handoff_count": complete_handoff_count,
            "total_handoff_count": total_handoff_count,
            "prerequisite_artifact": (
                "results/figures/meeteval_cpwer_execution_status_batch_handoff_completion_summary.md"
            ),
            "receipt_target": "results/figures/meeteval_cpwer_official_execution_completion_summary.md",
            "checklist_goal": (
                "Verify batch handoff completion before advancing official cpWER execution completion review."
            ),
            "bridge_note": (
                f"Batch handoff completion reports queue_status={queue_status} with "
                f"{complete_handoff_count}/{total_handoff_count} complete handoffs."
            ),
            "next_gate": "Confirm this bridge before opening the official cpWER execution completion summary.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Execution Status Batch Handoff Completion Summary Bridge Checklist",
        "",
        "This generated checklist connects batch handoff completion to official cpWER execution completion review. "
        "It does not claim official MeetEval evaluation or benchmark completion.",
        "",
        "| checklist_order | queue_status | complete_handoff_count | total_handoff_count | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['queue_status']} | {row['complete_handoff_count']} | "
            f"{row['total_handoff_count']} | {row['prerequisite_artifact']} | {row['receipt_target']} | "
            f"{row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = (
        tables_dir / "meeteval_cpwer_execution_status_batch_handoff_completion_summary_bridge_checklist.csv"
    )
    json_path = (
        tables_dir / "meeteval_cpwer_execution_status_batch_handoff_completion_summary_bridge_checklist.json"
    )
    md_path = (
        figures_dir / "meeteval_cpwer_execution_status_batch_handoff_completion_summary_bridge_checklist.md"
    )

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
        print("Batch handoff completion summary not found; bridge checklist not written.")
        return
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote MeetEval cpWER execution status batch handoff completion summary bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER execution status batch handoff completion summary bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER execution status batch handoff completion summary bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
