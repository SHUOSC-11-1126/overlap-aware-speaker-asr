from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "coordination_state",
    "operator_sequence",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_operator_summary() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_operator_next_action_summary.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(summary: dict[str, str]) -> list[dict[str, str]]:
    coordination_state = str(summary.get("coordination_state", "mixed_ready_state"))
    operator_sequence = str(summary.get("operator_sequence", ""))
    return [
        {
            "checklist_order": "1",
            "coordination_state": coordination_state,
            "operator_sequence": operator_sequence,
            "prerequisite_artifact": "results/figures/frontier_operator_next_action_handoff_packet.md",
            "receipt_target": "results/figures/frontier_operator_next_action_card.md",
            "checklist_goal": "Verify the top-level operator handoff packet before reopening the top-level operator card.",
            "bridge_note": (
                f"Top-level operator summary reports coordination_state={coordination_state} with "
                f"operator_sequence={operator_sequence}; confirm packet context before reopening the operator card."
            ),
            "next_gate": "Confirm this bridge before opening the top-level operator card again.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Operator Next-Action Handoff Packet Bridge Checklist",
        "",
        "This generated checklist turns the top-level operator handoff packet into a bridge verification path. "
        "It remains experimental/frontier coordination only and does not claim experiment completion.",
        "",
        "| checklist_order | coordination_state | operator_sequence | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['coordination_state']} | {row['operator_sequence']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_operator_next_action_handoff_packet_bridge_checklist.csv"
    json_path = tables_dir / "frontier_operator_next_action_handoff_packet_bridge_checklist.json"
    md_path = figures_dir / "frontier_operator_next_action_handoff_packet_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_operator_summary())
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote frontier operator next-action handoff packet bridge checklist CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier operator next-action handoff packet bridge checklist JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier operator next-action handoff packet bridge checklist note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
