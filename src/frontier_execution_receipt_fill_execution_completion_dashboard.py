from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


DASHBOARD_COLUMNS = [
    "current_first_frontier",
    "awaiting_fill_execution_count",
    "total_frontier_count",
    "combined_fill_execution_status",
    "dominant_blocker",
    "dashboard_note",
]


def load_operator_brief() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_fill_execution_operator_brief.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_completion_summary() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_fill_execution_completion_summary.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_dashboard_row(
    operator_brief: dict[str, str],
    completion_summary: dict[str, str],
) -> dict[str, str]:
    if not operator_brief or not completion_summary:
        return {}
    frontier = str(operator_brief.get("operator_frontier", "unknown"))
    awaiting = str(completion_summary.get("awaiting_fill_execution_count", "0"))
    total = str(completion_summary.get("total_frontier_count", "0"))
    combined = str(completion_summary.get("combined_fill_execution_status", "fill_execution_in_progress"))
    return {
        "current_first_frontier": frontier,
        "awaiting_fill_execution_count": awaiting,
        "total_frontier_count": total,
        "combined_fill_execution_status": combined,
        "dominant_blocker": "template_only_execution_receipts",
        "dashboard_note": (
            f"{frontier} leads the fill execution queue with {awaiting}/{total} frontiers still awaiting fill; "
            "no benchmark execution is claimed until receipts are filled."
        ),
    }


def build_dashboard_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Frontier Execution Receipt Fill Execution Completion Dashboard",
        "",
        "This generated dashboard summarizes the current fill execution queue state at a glance. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        f"- Current first frontier: `{row['current_first_frontier']}`",
        f"- Awaiting fill execution: `{row['awaiting_fill_execution_count']}/{row['total_frontier_count']}`",
        f"- Combined fill execution status: `{row['combined_fill_execution_status']}`",
        f"- Dominant blocker: `{row['dominant_blocker']}`",
        f"- Dashboard note: {row['dashboard_note']}",
    ]
    return lines


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_fill_execution_completion_dashboard.csv"
    json_path = tables_dir / "frontier_execution_receipt_fill_execution_completion_dashboard.json"
    md_path = figures_dir / "frontier_execution_receipt_fill_execution_completion_dashboard.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DASHBOARD_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_dashboard_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_dashboard_row(load_operator_brief(), load_completion_summary())
    if not row:
        print("Operator brief or completion summary not found; dashboard not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote frontier execution receipt fill execution completion dashboard CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution completion dashboard JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution completion dashboard note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
