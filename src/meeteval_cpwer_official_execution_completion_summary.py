from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


COMPLETION_COLUMNS = [
    "scope",
    "complete_count",
    "total_count",
    "tool_unavailable_count",
    "queue_status",
    "observation",
]


def load_official_execution_rows() -> list[dict[str, str]]:
    path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_official_execution.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_completion_summary_row(execution_rows: list[dict[str, str]]) -> dict[str, str]:
    total_count = len(execution_rows)
    complete_count = sum(
        1
        for row in execution_rows
        if row.get("execution_status") == "official_cpwer_narrow_dry_run_complete"
    )
    tool_unavailable_count = sum(
        1 for row in execution_rows if row.get("execution_status") == "official_cpwer_tool_unavailable"
    )
    if total_count == 0:
        queue_status = "queue_not_started"
    elif complete_count == total_count:
        queue_status = "queue_complete"
    elif complete_count > 0:
        queue_status = "queue_partial"
    elif tool_unavailable_count == total_count:
        queue_status = "queue_blocked_by_tool"
    else:
        queue_status = "queue_in_progress"
    return {
        "scope": "meeteval_cpwer_official_execution",
        "complete_count": str(complete_count),
        "total_count": str(total_count),
        "tool_unavailable_count": str(tool_unavailable_count),
        "queue_status": queue_status,
        "observation": (
            "Experimental/frontier official MeetEval cpWER narrow dry-run completion rollup; "
            "full MeetEval benchmark completion is not claimed."
        ),
    }


def build_completion_summary_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# MeetEval cpWER Official Execution Completion Summary",
        "",
        "This generated note summarizes official MeetEval cpWER narrow dry-run completion. "
        "It does not claim full MeetEval benchmark completion.",
        "",
        "| scope | complete_count | total_count | tool_unavailable_count | queue_status | observation |",
        "| --- | ---: | ---: | ---: | --- | --- |",
        (
            f"| {row['scope']} | {row['complete_count']} | {row['total_count']} | "
            f"{row['tool_unavailable_count']} | {row['queue_status']} | {row['observation']} |"
        ),
    ]
    return lines


def write_outputs(completion_row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_official_execution_completion_summary.csv"
    json_path = tables_dir / "meeteval_cpwer_official_execution_completion_summary.json"
    md_path = figures_dir / "meeteval_cpwer_official_execution_completion_summary.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COMPLETION_COLUMNS)
        writer.writeheader()
        writer.writerow(completion_row)
    json_path.write_text(json.dumps(completion_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_completion_summary_lines(completion_row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    completion_row = build_completion_summary_row(load_official_execution_rows())
    if completion_row["total_count"] == "0":
        print("Official execution output not found; completion summary not written.")
        return
    csv_path, json_path, md_path = write_outputs(completion_row)
    print(
        "Wrote MeetEval cpWER official execution completion summary CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER official execution completion summary JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER official execution completion summary note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )
    print(f"Queue status: {completion_row['queue_status']}")


if __name__ == "__main__":
    main()
