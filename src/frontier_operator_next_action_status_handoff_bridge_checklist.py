from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "action_lane",
    "frontier_name",
    "combined_operator_status",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_handoff_rows() -> list[dict[str, str]]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_operator_next_action_status_handoff.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_bridge_checklist_rows(handoff_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for handoff in handoff_rows:
        order = str(handoff.get("handoff_order", len(rows) + 1))
        action_lane = str(handoff.get("action_lane", ""))
        frontier_name = str(handoff.get("frontier_name", "unknown"))
        combined_status = str(handoff.get("combined_operator_status", "operator_status_unset"))
        receipt_target = str(handoff.get("expected_outputs", ""))
        rows.append(
            {
                "checklist_order": order,
                "action_lane": action_lane,
                "frontier_name": frontier_name,
                "combined_operator_status": combined_status,
                "prerequisite_artifact": "results/figures/frontier_operator_next_action_status_handoff.md",
                "receipt_target": receipt_target,
                "checklist_goal": (
                    f"Verify the top-level {action_lane} handoff for {frontier_name} before opening its target artifact."
                ),
                "bridge_note": (
                    f"Handoff reports combined_operator_status={combined_status} on {action_lane} for {frontier_name}; "
                    "confirm lane-specific operator context before opening the target artifact."
                ),
                "next_gate": f"Confirm this bridge before advancing the {frontier_name} top-level operator target.",
            }
        )
    return rows


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Operator Next-Action Status Handoff Bridge Checklist",
        "",
        "This generated checklist turns the top-level operator status handoff into a row-by-row bridge verification path. "
        "It remains experimental/frontier coordination only and does not claim experiment completion.",
        "",
        "| checklist_order | action_lane | frontier_name | combined_operator_status | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['action_lane']} | {row['frontier_name']} | "
            f"{row['combined_operator_status']} | {row['prerequisite_artifact']} | {row['receipt_target']} | "
            f"{row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_operator_next_action_status_handoff_bridge_checklist.csv"
    json_path = tables_dir / "frontier_operator_next_action_status_handoff_bridge_checklist.json"
    md_path = figures_dir / "frontier_operator_next_action_status_handoff_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_handoff_rows())
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote frontier operator next-action status handoff bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier operator next-action status handoff bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier operator next-action status handoff bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
