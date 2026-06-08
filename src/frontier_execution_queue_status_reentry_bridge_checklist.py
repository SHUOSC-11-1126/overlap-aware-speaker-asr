from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "current_first_frontier",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_status_reentry_card() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_queue_status_reentry_card.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(reentry_card: dict[str, str]) -> list[dict[str, str]]:
    if not reentry_card:
        return []
    frontier = str(reentry_card.get("current_first_frontier", "unknown"))
    reentry_action = str(reentry_card.get("reentry_action", ""))
    return [
        {
            "checklist_order": "1",
            "current_first_frontier": frontier,
            "prerequisite_artifact": "results/figures/frontier_execution_queue_status_reentry_card.md",
            "receipt_target": "results/figures/frontier_execution_queue_handoff_bridge_checklist.md",
            "checklist_goal": (
                f"Verify the execution queue status reentry card for {frontier} before opening the handoff bridge."
            ),
            "bridge_note": (
                f"Confirm the reentry action before opening the handoff bridge: {reentry_action} "
                "This bridge remains coordination-only and does not claim benchmark execution."
            ),
            "next_gate": "Confirm this bridge before opening the execution queue handoff bridge target.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    return [
        "# Frontier Execution Queue Status Reentry Bridge Checklist",
        "",
        "This generated checklist connects the status reentry card to the execution queue handoff bridge. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        "| checklist_order | current_first_frontier | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        *[
            f"| {row['checklist_order']} | {row['current_first_frontier']} | {row['prerequisite_artifact']} | "
            f"{row['receipt_target']} | {row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
            for row in rows
        ],
    ]


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_queue_status_reentry_bridge_checklist.csv"
    json_path = tables_dir / "frontier_execution_queue_status_reentry_bridge_checklist.json"
    md_path = figures_dir / "frontier_execution_queue_status_reentry_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_status_reentry_card())
    if not rows:
        print("Execution queue status reentry card not found; reentry bridge checklist not written.")
        return
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote frontier execution queue status reentry bridge checklist CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue status reentry bridge checklist JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue status reentry bridge checklist note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
