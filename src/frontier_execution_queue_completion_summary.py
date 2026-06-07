from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


COMPLETION_COLUMNS = [
    "scope",
    "ready_chain_count",
    "total_chain_count",
    "pending_chain_count",
    "queue_status",
    "observation",
]

CHAIN_KEYS = [
    "meeteval_chain_status",
    "speaker_profile_chain_status",
    "external_staging_chain_status",
]


def load_status_row() -> dict[str, str]:
    status_path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_queue_status.json"
    if not status_path.exists():
        return {}
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def count_ready_chains(status_row: dict[str, str]) -> tuple[int, int]:
    total = len(CHAIN_KEYS)
    ready = sum(1 for key in CHAIN_KEYS if status_row.get(key) == "execution_chain_ready")
    return ready, total


def build_completion_summary_row(status_row: dict[str, str]) -> dict[str, str]:
    ready_count, total_count = count_ready_chains(status_row)
    pending_count = total_count - ready_count
    queue_status = "queue_complete" if pending_count == 0 else "queue_in_progress"
    return {
        "scope": "frontier_execution_coordination_queue",
        "ready_chain_count": str(ready_count),
        "total_chain_count": str(total_count),
        "pending_chain_count": str(pending_count),
        "queue_status": queue_status,
        "observation": (
            "Experimental/frontier execution coordination queue completion rollup; "
            "no official benchmark execution or external audio staging is claimed."
        ),
    }


def build_completion_summary_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Frontier Execution Queue Completion Summary",
        "",
        "This generated note summarizes frontier execution coordination queue completion. "
        "It does not claim benchmark execution or external audio staging.",
        "",
        "| scope | ready_chain_count | total_chain_count | pending_chain_count | queue_status | observation |",
        "| --- | ---: | ---: | ---: | --- | --- |",
        (
            f"| {row['scope']} | {row['ready_chain_count']} | {row['total_chain_count']} | "
            f"{row['pending_chain_count']} | {row['queue_status']} | {row['observation']} |"
        ),
    ]
    return lines


def write_outputs(completion_row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_queue_completion_summary.csv"
    json_path = tables_dir / "frontier_execution_queue_completion_summary.json"
    md_path = figures_dir / "frontier_execution_queue_completion_summary.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COMPLETION_COLUMNS)
        writer.writeheader()
        writer.writerow(completion_row)
    json_path.write_text(json.dumps(completion_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_completion_summary_lines(completion_row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    status_row = load_status_row()
    completion_row = build_completion_summary_row(status_row)
    csv_path, json_path, md_path = write_outputs(completion_row)
    print(f"Wrote frontier execution queue completion summary CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue completion summary JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue completion summary note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Queue status: {completion_row['queue_status']}")


if __name__ == "__main__":
    main()
