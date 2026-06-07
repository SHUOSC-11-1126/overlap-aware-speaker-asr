from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "fill_execution_frontier",
    "frontier_queue_head",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_frontier_bridge() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_fill_execution_frontier_bridge.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(bridge_row: dict[str, str]) -> list[dict[str, str]]:
    if not bridge_row:
        return []
    frontier = str(bridge_row.get("fill_execution_frontier", "unknown"))
    queue_head = str(bridge_row.get("frontier_queue_head", "unknown"))
    return [
        {
            "checklist_order": "1",
            "fill_execution_frontier": frontier,
            "frontier_queue_head": queue_head,
            "prerequisite_artifact": "results/figures/frontier_execution_receipt_fill_execution_frontier_bridge.md",
            "receipt_target": "results/figures/frontier_execution_receipt_fill_execution_runbook_card.md",
            "checklist_goal": (
                f"Verify the frontier bridge alignment between {frontier} and {queue_head} before fill execution."
            ),
            "bridge_note": str(bridge_row.get("bridge_note", "")),
            "next_gate": "Confirm this bridge before opening the runbook card.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Execution Receipt Fill Execution Frontier Bridge Checklist",
        "",
        "This generated checklist turns the frontier bridge into an ordered verification path. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        "| checklist_order | fill_execution_frontier | frontier_queue_head | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['fill_execution_frontier']} | {row['frontier_queue_head']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_fill_execution_frontier_bridge_checklist.csv"
    json_path = tables_dir / "frontier_execution_receipt_fill_execution_frontier_bridge_checklist.json"
    md_path = figures_dir / "frontier_execution_receipt_fill_execution_frontier_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_frontier_bridge())
    if not rows:
        print("Frontier bridge not found; bridge checklist not written.")
        return
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote frontier execution receipt fill execution frontier bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution frontier bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution frontier bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
