from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


DASHBOARD_COLUMNS = [
    "current_first_frontier",
    "next_milestone",
    "remaining_frontier_count",
    "dominant_blocker",
    "dashboard_note",
]


def load_operator_brief() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_queue_operator_brief.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_milestone_card() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_queue_milestone_card.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_dashboard_row(
    operator_brief: dict[str, str],
    milestone_card: dict[str, str],
) -> dict[str, str]:
    if not operator_brief or not milestone_card:
        return {}
    current_first_frontier = str(operator_brief.get("operator_frontier", ""))
    next_milestone = str(milestone_card.get("next_milestone", ""))
    remaining_frontier_count = str(milestone_card.get("remaining_frontier_count", "0"))
    return {
        "current_first_frontier": current_first_frontier,
        "next_milestone": next_milestone,
        "remaining_frontier_count": remaining_frontier_count,
        "dominant_blocker": "execution_receipt_fill_pending",
        "dashboard_note": (
            f"{current_first_frontier or 'The current frontier'} leads the execution queue while "
            "execution receipts remain the dominant coordination blocker. "
            "This remains coordination-only and does not claim benchmark execution."
        ),
    }


def build_dashboard_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Frontier Execution Queue Completion Dashboard",
        "",
        "This generated dashboard summarizes the current execution queue state at a glance. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        f"- Current first frontier: `{row['current_first_frontier']}`",
        f"- Next milestone: `{row['next_milestone']}`",
        f"- Remaining frontier count after milestone: `{row['remaining_frontier_count']}`",
        f"- Dominant blocker: `{row['dominant_blocker']}`",
        f"- Dashboard note: {row['dashboard_note']}",
    ]


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_queue_completion_dashboard.csv"
    json_path = tables_dir / "frontier_execution_queue_completion_dashboard.json"
    md_path = figures_dir / "frontier_execution_queue_completion_dashboard.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DASHBOARD_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_dashboard_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_dashboard_row(load_operator_brief(), load_milestone_card())
    if not row:
        print("Execution queue operator brief or milestone card not found; completion dashboard not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(f"Wrote frontier execution queue completion dashboard CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue completion dashboard JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue completion dashboard note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
