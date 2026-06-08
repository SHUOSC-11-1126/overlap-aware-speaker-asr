from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


PACKET_COLUMNS = [
    "packet_order",
    "section_name",
    "artifact_path",
    "section_role",
    "packet_note",
]


PACKET_SECTIONS = [
    ("1", "status", "results/figures/frontier_operator_next_action_status.md", "Top-level operator status snapshot"),
    (
        "2",
        "status_bridge_checklist",
        "results/figures/frontier_operator_next_action_status_bridge_checklist.md",
        "Verify the status snapshot before opening the broader operator handoff packet",
    ),
    (
        "3",
        "status_handoff",
        "results/figures/frontier_operator_next_action_status_handoff.md",
        "Lane-specific ready/block top-level operator actions",
    ),
    (
        "4",
        "status_handoff_bridge_checklist",
        "results/figures/frontier_operator_next_action_status_handoff_bridge_checklist.md",
        "Verify each lane-specific handoff before opening its target artifact",
    ),
    (
        "5",
        "status_handoff_completion_summary",
        "results/figures/frontier_operator_next_action_status_handoff_completion_summary.md",
        "Queue-level rollup of visible ready and blocked lanes",
    ),
    (
        "6",
        "status_handoff_completion_summary_bridge_checklist",
        "results/figures/frontier_operator_next_action_status_handoff_completion_summary_bridge_checklist.md",
        "Verify queue-level handoff closure before reopening the lane-level handoff",
    ),
]


def load_completion_summary() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_operator_next_action_status_handoff_completion_summary.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_packet_rows(summary: dict[str, str]) -> list[dict[str, str]]:
    queue_status = str(summary.get("queue_status", "queue_empty"))
    ready_count = str(summary.get("ready_lane_count", "0"))
    blocked_count = str(summary.get("blocked_lane_count", "0"))
    rows: list[dict[str, str]] = []
    for order, section_name, artifact_path, section_role in PACKET_SECTIONS:
        rows.append(
            {
                "packet_order": order,
                "section_name": section_name,
                "artifact_path": artifact_path,
                "section_role": section_role,
                "packet_note": (
                    f"Top-level operator status handoff packet section while queue_status={queue_status}, "
                    f"ready_lane_count={ready_count}, blocked_lane_count={blocked_count}; "
                    "no frontier execution is claimed."
                ),
            }
        )
    return rows


def build_packet_lines(rows: list[dict[str, str]], summary: dict[str, str]) -> list[str]:
    queue_status = str(summary.get("queue_status", "queue_empty"))
    return [
        "# Frontier Operator Next-Action Status Handoff Packet",
        "",
        "This generated note provides a single entrypoint for the top-level operator status handoff stack. "
        "It remains experimental/frontier coordination only and does not claim experiment completion.",
        "",
        f"Current rollup: `queue_status = {queue_status}`.",
        "",
        "| packet_order | section_name | artifact_path | section_role | packet_note |",
        "| --- | --- | --- | --- | --- |",
        *[
            f"| {row['packet_order']} | {row['section_name']} | {row['artifact_path']} | "
            f"{row['section_role']} | {row['packet_note']} |"
            for row in rows
        ],
    ]


def write_outputs(rows: list[dict[str, str]], summary: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_operator_next_action_status_handoff_packet.csv"
    json_path = tables_dir / "frontier_operator_next_action_status_handoff_packet.json"
    md_path = figures_dir / "frontier_operator_next_action_status_handoff_packet.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=PACKET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_packet_lines(rows, summary)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    summary = load_completion_summary()
    rows = build_packet_rows(summary)
    csv_path, json_path, md_path = write_outputs(rows, summary)
    print(
        "Wrote frontier operator next-action status handoff packet CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier operator next-action status handoff packet JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier operator next-action status handoff packet note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
