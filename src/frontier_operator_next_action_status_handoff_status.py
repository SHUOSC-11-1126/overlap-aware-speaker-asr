from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


STATUS_COLUMNS = [
    "scope",
    "queue_status",
    "ready_lane_status",
    "blocked_lane_status",
    "milestone_status",
    "dashboard_bridge_status",
    "combined_status_handoff_state",
    "primary_status_target",
    "status_note",
]


def load_json_payload(path_rel: str) -> dict | list:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, (dict, list)) else {}


def build_status_row(
    summary: dict[str, str],
    milestone: dict[str, str],
    dashboard: dict[str, str],
    dashboard_bridge_rows: list[dict[str, str]],
) -> dict[str, str]:
    queue_status = str(summary.get("queue_status", "queue_empty"))
    ready_lane_count = int(summary.get("ready_lane_count", "0") or "0")
    blocked_lane_count = int(summary.get("blocked_lane_count", "0") or "0")
    next_milestone = str(milestone.get("next_milestone", ""))
    current_frontier = str(dashboard.get("current_first_frontier", "")) or str(summary.get("primary_frontier", ""))

    ready_lane_status = "ready_lane_active" if ready_lane_count > 0 else "ready_lane_empty"
    blocked_lane_status = "blocked_lane_waiting" if blocked_lane_count > 0 else "blocked_lane_clear"
    milestone_status = "milestone_active" if next_milestone else "milestone_missing"
    dashboard_bridge_status = (
        "dashboard_bridge_ready" if current_frontier and dashboard_bridge_rows else "dashboard_bridge_missing"
    )

    if (
        ready_lane_status == "ready_lane_active"
        and blocked_lane_status == "blocked_lane_waiting"
        and milestone_status == "milestone_active"
        and dashboard_bridge_status == "dashboard_bridge_ready"
    ):
        combined_status_handoff_state = "status_handoff_mixed_ready"
    elif ready_lane_status == "ready_lane_active" and milestone_status == "milestone_active":
        combined_status_handoff_state = "status_handoff_ready_lane_only"
    elif blocked_lane_status == "blocked_lane_waiting" and ready_lane_status == "ready_lane_empty":
        combined_status_handoff_state = "status_handoff_blocked_lane_only"
    else:
        combined_status_handoff_state = "status_handoff_unset"

    blocked_note = "a blocked lane remains visible" if blocked_lane_count > 0 else "no blocked lane remains visible"
    return {
        "scope": "frontier_operator_next_action_status_handoff_status",
        "queue_status": queue_status,
        "ready_lane_status": ready_lane_status,
        "blocked_lane_status": blocked_lane_status,
        "milestone_status": milestone_status,
        "dashboard_bridge_status": dashboard_bridge_status,
        "combined_status_handoff_state": combined_status_handoff_state,
        "primary_status_target": current_frontier,
        "status_note": (
            f"{current_frontier or 'No ready frontier'} remains the primary status/handoff coordination target while "
            f"{blocked_note}. This is a coordination-only status rollup and does not claim frontier execution."
        ),
    }


def build_status_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Frontier Operator Next-Action Status Handoff Status",
        "",
        "This generated status note compresses the top-level status/handoff subchain into one machine-readable rollup. "
        "It remains experimental/frontier coordination only and does not claim experiment completion.",
        "",
        "| scope | queue_status | ready_lane_status | blocked_lane_status | milestone_status | dashboard_bridge_status | combined_status_handoff_state | primary_status_target | status_note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['scope']} | {row['queue_status']} | {row['ready_lane_status']} | "
            f"{row['blocked_lane_status']} | {row['milestone_status']} | {row['dashboard_bridge_status']} | "
            f"{row['combined_status_handoff_state']} | {row['primary_status_target']} | {row['status_note']} |"
        ),
    ]


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_operator_next_action_status_handoff_status.csv"
    json_path = tables_dir / "frontier_operator_next_action_status_handoff_status.json"
    md_path = figures_dir / "frontier_operator_next_action_status_handoff_status.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=STATUS_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_status_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    summary_payload = load_json_payload("results/tables/frontier_operator_next_action_status_handoff_completion_summary.json")
    milestone_payload = load_json_payload("results/tables/frontier_operator_next_action_status_handoff_milestone_card.json")
    dashboard_payload = load_json_payload("results/tables/frontier_operator_next_action_status_handoff_completion_dashboard.json")
    bridge_payload = load_json_payload(
        "results/tables/frontier_operator_next_action_status_handoff_completion_dashboard_bridge_checklist.json"
    )
    row = build_status_row(
        summary_payload if isinstance(summary_payload, dict) else {},
        milestone_payload if isinstance(milestone_payload, dict) else {},
        dashboard_payload if isinstance(dashboard_payload, dict) else {},
        bridge_payload if isinstance(bridge_payload, list) else [],
    )
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote frontier operator next-action status handoff status CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier operator next-action status handoff status JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier operator next-action status handoff status note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )
    print(f"Combined status/handoff state: {row['combined_status_handoff_state']}")


if __name__ == "__main__":
    main()
