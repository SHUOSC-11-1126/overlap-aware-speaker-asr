from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


COMPLETION_COLUMNS = [
    "scope",
    "awaiting_fill_execution_count",
    "total_frontier_count",
    "fill_execution_complete_count",
    "combined_fill_execution_status",
    "observation",
]

FRONTIER_STATUS_KEYS = [
    "meeteval_fill_execution_status",
    "speaker_profile_fill_execution_status",
    "external_staging_fill_execution_status",
]


def load_execution_status() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_fill_execution_status.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_completion_summary_row(status_row: dict[str, str]) -> dict[str, str]:
    statuses = [str(status_row.get(key, "receipt_missing")) for key in FRONTIER_STATUS_KEYS]
    total = str(len(statuses))
    awaiting = str(sum(1 for status in statuses if status == "awaiting_fill"))
    complete = str(sum(1 for status in statuses if status == "fill_complete"))
    combined = str(status_row.get("combined_fill_execution_status", "fill_execution_in_progress"))
    return {
        "scope": "frontier_execution_receipt_fill_execution_coordination_queue",
        "awaiting_fill_execution_count": awaiting,
        "total_frontier_count": total,
        "fill_execution_complete_count": complete,
        "combined_fill_execution_status": combined,
        "observation": (
            "Experimental/frontier receipt-fill execution coordination queue completion rollup; "
            "template-only receipts remain unfilled and no benchmark execution is claimed."
        ),
    }


def build_completion_summary_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Frontier Execution Receipt Fill Execution Completion Summary",
        "",
        "This generated note summarizes frontier receipt-fill execution coordination queue completion. "
        "It does not claim benchmark execution.",
        "",
        "| scope | awaiting_fill_execution_count | total_frontier_count | fill_execution_complete_count | combined_fill_execution_status | observation |",
        "| --- | ---: | ---: | ---: | --- | --- |",
        (
            f"| {row['scope']} | {row['awaiting_fill_execution_count']} | {row['total_frontier_count']} | "
            f"{row['fill_execution_complete_count']} | {row['combined_fill_execution_status']} | {row['observation']} |"
        ),
    ]
    return lines


def write_outputs(completion_row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_fill_execution_completion_summary.csv"
    json_path = tables_dir / "frontier_execution_receipt_fill_execution_completion_summary.json"
    md_path = figures_dir / "frontier_execution_receipt_fill_execution_completion_summary.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COMPLETION_COLUMNS)
        writer.writeheader()
        writer.writerow(completion_row)
    json_path.write_text(json.dumps(completion_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_completion_summary_lines(completion_row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    completion_row = build_completion_summary_row(load_execution_status())
    csv_path, json_path, md_path = write_outputs(completion_row)
    print(
        "Wrote frontier execution receipt fill execution completion summary CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution completion summary JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution completion summary note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )
    print(f"Combined fill execution status: {completion_row['combined_fill_execution_status']}")


if __name__ == "__main__":
    main()
