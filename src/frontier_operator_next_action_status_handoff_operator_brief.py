from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


OPERATOR_BRIEF_COLUMNS = [
    "ready_frontier",
    "ready_action",
    "ready_target",
    "blocked_frontier",
    "blocked_target",
    "operator_evidence",
    "operator_urgency",
    "operator_note",
]


def load_completion_summary() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_operator_next_action_status_handoff_completion_summary.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_handoff_rows() -> list[dict[str, str]]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_operator_next_action_status_handoff.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_operator_brief_row(
    summary: dict[str, str],
    handoff_rows: list[dict[str, str]],
) -> dict[str, str]:
    if not handoff_rows:
        return {}
    ready_row = next((row for row in handoff_rows if row.get("action_lane") == "ready_lane"), {})
    blocked_row = next((row for row in handoff_rows if row.get("action_lane") == "blocked_lane"), {})
    if not ready_row and not blocked_row:
        return {}
    queue_status = str(summary.get("queue_status", "queue_empty"))
    ready_count = str(summary.get("ready_lane_count", "0"))
    blocked_count = str(summary.get("blocked_lane_count", "0"))
    return {
        "ready_frontier": str(ready_row.get("frontier_name", "")),
        "ready_action": str(ready_row.get("recommended_action", "")),
        "ready_target": str(ready_row.get("expected_outputs", "")),
        "blocked_frontier": str(blocked_row.get("frontier_name", "")),
        "blocked_target": str(blocked_row.get("expected_outputs", "")),
        "operator_evidence": (
            "results/figures/frontier_operator_next_action_status_handoff.md; "
            "results/figures/frontier_operator_next_action_status_handoff_bridge_checklist.md"
        ),
        "operator_urgency": (
            f"queue_status={queue_status}; ready_lane_count={ready_count}; blocked_lane_count={blocked_count}"
        ),
        "operator_note": (
            f"Advance {str(ready_row.get('frontier_name', 'the ready lane'))} first while keeping "
            f"{str(blocked_row.get('frontier_name', 'the blocked lane'))} visible as the current unblock target. "
            "This remains coordination-only and does not claim frontier execution."
        ),
    }


def build_operator_brief_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Frontier Operator Next-Action Status Handoff Operator Brief",
        "",
        "This generated brief gives the current top-level operator a plain-language next step summary for the status/handoff subchain. "
        "It remains experimental/frontier coordination only and does not claim experiment completion.",
        "",
        f"- Ready frontier: `{row['ready_frontier']}`",
        f"- Ready action: `{row['ready_action']}`",
        f"- Ready target: `{row['ready_target']}`",
        f"- Blocked frontier: `{row['blocked_frontier']}`",
        f"- Blocked target: `{row['blocked_target']}`",
        f"- Evidence path: `{row['operator_evidence']}`",
        f"- Urgency: {row['operator_urgency']}",
        f"- Operator note: {row['operator_note']}",
    ]


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_operator_next_action_status_handoff_operator_brief.csv"
    json_path = tables_dir / "frontier_operator_next_action_status_handoff_operator_brief.json"
    md_path = figures_dir / "frontier_operator_next_action_status_handoff_operator_brief.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OPERATOR_BRIEF_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_operator_brief_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_operator_brief_row(load_completion_summary(), load_handoff_rows())
    if not row:
        print("No status handoff rows found; operator brief not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote frontier operator next-action status handoff operator brief CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier operator next-action status handoff operator brief JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier operator next-action status handoff operator brief note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
