from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "frontier_name",
    "readiness_state",
    "prerequisite_artifact",
    "receipt_queue_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_readiness_rows() -> list[dict[str, str]]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_queue_receipt_readiness_board.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_bridge_checklist_rows(readiness_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for order, readiness in enumerate(readiness_rows, start=1):
        frontier_name = str(readiness.get("frontier_name", "unknown"))
        readiness_state = str(readiness.get("readiness_state", "bridge_or_scaffold_pending"))
        rows.append(
            {
                "checklist_order": str(order),
                "frontier_name": frontier_name,
                "readiness_state": readiness_state,
                "prerequisite_artifact": "results/figures/frontier_execution_queue_receipt_readiness_board.md",
                "receipt_queue_target": "results/figures/frontier_execution_receipt_queue_status.md",
                "checklist_goal": (
                    f"Verify receipt readiness for {frontier_name} before reopening the unified receipt queue status."
                ),
                "bridge_note": (
                    f"Receipt readiness board reports readiness_state={readiness_state} for {frontier_name}; "
                    "confirm this state before advancing into the unified frontier receipt queue."
                ),
                "next_gate": "Confirm this bridge before claiming receipt-queue readiness for this frontier.",
            }
        )
    return rows


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Execution Queue Receipt Readiness Bridge Checklist",
        "",
        "This generated checklist connects the execution queue receipt readiness board to the unified receipt queue status view. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        "| checklist_order | frontier_name | readiness_state | prerequisite_artifact | receipt_queue_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['frontier_name']} | {row['readiness_state']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_queue_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_queue_receipt_readiness_bridge_checklist.csv"
    json_path = tables_dir / "frontier_execution_queue_receipt_readiness_bridge_checklist.json"
    md_path = figures_dir / "frontier_execution_queue_receipt_readiness_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_readiness_rows())
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote frontier execution queue receipt readiness bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution queue receipt readiness bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution queue receipt readiness bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
