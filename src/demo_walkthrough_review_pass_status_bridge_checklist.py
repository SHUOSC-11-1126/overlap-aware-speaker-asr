from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "queue_status",
    "completed_count",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_status_row() -> dict[str, str]:
    status_path = PROJECT_ROOT / "results" / "tables" / "demo_walkthrough_review_pass_status.json"
    if not status_path.exists():
        return {}
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(status_row: dict[str, str]) -> list[dict[str, str]]:
    queue_status = str(status_row.get("queue_status", "queue_in_progress"))
    completed_count = str(status_row.get("completed_count", "0"))
    return [
        {
            "checklist_order": "1",
            "queue_status": queue_status,
            "completed_count": completed_count,
            "prerequisite_artifact": "results/figures/demo_walkthrough_review_pass_status.md",
            "receipt_target": "results/figures/demo_walkthrough_review_pass_final_bridge_checklist.md",
            "checklist_goal": (
                "Verify the walkthrough review status bridge before opening the final pass bridge checklist."
            ),
            "bridge_note": (
                f"Status rollup reports queue_status={queue_status} with completed_count={completed_count}; "
                "confirm queue completion before advancing the final bridge."
            ),
            "next_gate": "Confirm this bridge before opening the demo walkthrough review pass final bridge checklist target.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Demo Walkthrough Review Pass Status Bridge Checklist",
        "",
        "This generated checklist turns the walkthrough review status rollup into a row-by-row bridge verification path. "
        "It remains qualitative/demo only and does not claim live demo or recording delivery.",
        "",
        "| checklist_order | queue_status | completed_count | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['queue_status']} | {row['completed_count']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "demo_walkthrough_review_pass_status_bridge_checklist.csv"
    json_path = tables_dir / "demo_walkthrough_review_pass_status_bridge_checklist.json"
    md_path = figures_dir / "demo_walkthrough_review_pass_status_bridge_checklist.md"

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
    print(f"Wrote demo walkthrough review pass status bridge checklist CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo walkthrough review pass status bridge checklist JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo walkthrough review pass status bridge checklist note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
