from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "checkpoint_frontier",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_phase_checkpoint_card() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_queue_phase_checkpoint_card.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(phase_checkpoint: dict[str, str]) -> list[dict[str, str]]:
    if not phase_checkpoint:
        return []
    frontier = str(phase_checkpoint.get("checkpoint_frontier", "unknown"))
    completion_signal = str(phase_checkpoint.get("completion_signal", ""))
    return [
        {
            "checklist_order": "1",
            "checkpoint_frontier": frontier,
            "prerequisite_artifact": "results/figures/frontier_execution_queue_phase_checkpoint_card.md",
            "receipt_target": "results/figures/frontier_execution_queue_milestone_card.md",
            "checklist_goal": (
                f"Verify the phase checkpoint card for {frontier} before opening the milestone card."
            ),
            "bridge_note": (
                f"Confirm the phase checkpoint completion signal for {frontier}: {completion_signal}. "
                "This bridge remains coordination-only and does not claim benchmark execution."
            ),
            "next_gate": "Confirm this bridge before opening the milestone card target.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    return [
        "# Frontier Execution Queue Phase Checkpoint Bridge Checklist",
        "",
        "This generated checklist connects the phase checkpoint card to the milestone card target. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        "| checklist_order | checkpoint_frontier | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        *[
            f"| {row['checklist_order']} | {row['checkpoint_frontier']} | {row['prerequisite_artifact']} | "
            f"{row['receipt_target']} | {row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
            for row in rows
        ],
    ]


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_queue_phase_checkpoint_bridge_checklist.csv"
    json_path = tables_dir / "frontier_execution_queue_phase_checkpoint_bridge_checklist.json"
    md_path = figures_dir / "frontier_execution_queue_phase_checkpoint_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_phase_checkpoint_card())
    if not rows:
        print("Execution queue phase checkpoint card not found; phase checkpoint bridge checklist not written.")
        return
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote frontier execution queue phase checkpoint bridge checklist CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue phase checkpoint bridge checklist JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue phase checkpoint bridge checklist note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
