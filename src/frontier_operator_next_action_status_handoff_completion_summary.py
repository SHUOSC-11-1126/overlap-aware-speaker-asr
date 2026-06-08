from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


COMPLETION_COLUMNS = [
    "scope",
    "ready_lane_count",
    "blocked_lane_count",
    "total_lane_count",
    "queue_status",
    "primary_frontier",
    "observation",
]


def load_handoff_rows() -> list[dict[str, str]]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_operator_next_action_status_handoff.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_completion_summary_row(handoff_rows: list[dict[str, str]]) -> dict[str, str]:
    ready_count = sum(1 for row in handoff_rows if str(row.get("action_lane", "")) == "ready_lane")
    blocked_count = sum(1 for row in handoff_rows if str(row.get("action_lane", "")) == "blocked_lane")
    total_count = len(handoff_rows)

    if ready_count and blocked_count:
        queue_status = "queue_complete"
    elif ready_count:
        queue_status = "queue_ready_only"
    elif blocked_count:
        queue_status = "queue_blocked_only"
    else:
        queue_status = "queue_empty"

    primary_frontier = str(handoff_rows[0].get("frontier_name", "")) if handoff_rows else ""
    return {
        "scope": "frontier_operator_next_action_status_handoff",
        "ready_lane_count": str(ready_count),
        "blocked_lane_count": str(blocked_count),
        "total_lane_count": str(total_count),
        "queue_status": queue_status,
        "primary_frontier": primary_frontier,
        "observation": (
            "Experimental/frontier top-level operator handoff completion rollup; "
            "it summarizes lane visibility only and does not claim frontier execution."
        ),
    }


def build_completion_summary_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Frontier Operator Next-Action Status Handoff Completion Summary",
        "",
        "This generated note summarizes top-level operator status handoff completion. "
        "It remains experimental/frontier coordination only and does not claim experiment completion.",
        "",
        "| scope | ready_lane_count | blocked_lane_count | total_lane_count | queue_status | primary_frontier | observation |",
        "| --- | ---: | ---: | ---: | --- | --- | --- |",
        (
            f"| {row['scope']} | {row['ready_lane_count']} | {row['blocked_lane_count']} | "
            f"{row['total_lane_count']} | {row['queue_status']} | {row['primary_frontier']} | {row['observation']} |"
        ),
    ]


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_operator_next_action_status_handoff_completion_summary.csv"
    json_path = tables_dir / "frontier_operator_next_action_status_handoff_completion_summary.json"
    md_path = figures_dir / "frontier_operator_next_action_status_handoff_completion_summary.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COMPLETION_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_completion_summary_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_completion_summary_row(load_handoff_rows())
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote frontier operator next-action status handoff completion summary CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier operator next-action status handoff completion summary JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier operator next-action status handoff completion summary note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )
    print(f"Queue status: {row['queue_status']}")


if __name__ == "__main__":
    main()
