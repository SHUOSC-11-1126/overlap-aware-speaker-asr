from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "reentry_frontier",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_operator_brief() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_operator_next_action_status_handoff_operator_brief.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(operator_brief: dict[str, str]) -> list[dict[str, str]]:
    ready_frontier = str(operator_brief.get("ready_frontier", "unknown"))
    operator_urgency = str(operator_brief.get("operator_urgency", "queue_status=queue_empty"))
    return [
        {
            "checklist_order": "1",
            "reentry_frontier": ready_frontier,
            "prerequisite_artifact": "results/figures/frontier_operator_next_action_status_handoff_packet.md",
            "receipt_target": "results/figures/frontier_operator_next_action_status_handoff_operator_brief.md",
            "checklist_goal": (
                "Verify the top-level operator status handoff packet before reopening the status/handoff operator brief."
            ),
            "bridge_note": (
                f"Packet context reports ready_frontier={ready_frontier}; "
                f"operator_urgency={operator_urgency}. "
                "Confirm packet context before reopening the status/handoff operator brief."
            ),
            "next_gate": "Confirm this bridge before opening the frontier operator next-action status handoff operator brief target.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Operator Next-Action Status Handoff Packet Bridge Checklist",
        "",
        "This generated checklist turns the top-level operator status handoff packet into a bridge verification path. "
        "It remains experimental/frontier coordination only and does not claim experiment completion.",
        "",
        "| checklist_order | reentry_frontier | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['reentry_frontier']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | "
            f"{row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_operator_next_action_status_handoff_packet_bridge_checklist.csv"
    json_path = tables_dir / "frontier_operator_next_action_status_handoff_packet_bridge_checklist.json"
    md_path = figures_dir / "frontier_operator_next_action_status_handoff_packet_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_operator_brief())
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote frontier operator next-action status handoff packet bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier operator next-action status handoff packet bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier operator next-action status handoff packet bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
