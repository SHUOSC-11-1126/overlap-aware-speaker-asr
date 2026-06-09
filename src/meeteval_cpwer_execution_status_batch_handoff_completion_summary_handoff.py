from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


HANDOFF_COLUMNS = [
    "handoff_order",
    "handoff_status",
    "queue_status",
    "complete_handoff_count",
    "total_handoff_count",
    "handoff_target",
    "handoff_goal",
    "expected_evidence",
    "handoff_note",
]


def load_completion_summary() -> dict[str, str]:
    path = (
        PROJECT_ROOT
        / "results"
        / "tables"
        / "meeteval_cpwer_execution_status_batch_handoff_completion_summary.json"
    )
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_handoff_rows(summary: dict[str, str]) -> list[dict[str, str]]:
    if not summary:
        return []
    queue_status = str(summary.get("queue_status", "queue_in_progress"))
    complete_handoff_count = str(summary.get("complete_handoff_count", "0"))
    total_handoff_count = str(summary.get("total_handoff_count", "0"))
    ready = queue_status == "queue_complete" and int(complete_handoff_count or 0) == int(total_handoff_count or 0)
    return [
        {
            "handoff_order": "1",
            "handoff_status": "batch_handoff_completion_handoff_ready" if ready else "batch_handoff_completion_handoff_pending",
            "queue_status": queue_status,
            "complete_handoff_count": complete_handoff_count,
            "total_handoff_count": total_handoff_count,
            "handoff_target": "results/figures/meeteval_cpwer_official_execution_completion_summary.md",
            "handoff_goal": (
                "Advance official cpWER execution completion review after batch handoff completion rollup."
            ),
            "expected_evidence": "results/tables/meeteval_cpwer_official_execution_completion_summary.csv",
            "handoff_note": (
                "experimental/frontier batch handoff completion handoff only; "
                "official MeetEval benchmark completion is not claimed."
            ),
        }
    ]


def build_handoff_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Execution Status Batch Handoff Completion Summary Handoff",
        "",
        "This generated handoff turns batch handoff completion into an official cpWER execution completion action. "
        "It does not claim official MeetEval evaluation or benchmark completion.",
        "",
        "| handoff_order | handoff_status | queue_status | complete_handoff_count | total_handoff_count | handoff_target | handoff_goal | expected_evidence | handoff_note |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['handoff_order']} | {row['handoff_status']} | {row['queue_status']} | "
            f"{row['complete_handoff_count']} | {row['total_handoff_count']} | {row['handoff_target']} | "
            f"{row['handoff_goal']} | {row['expected_evidence']} | {row['handoff_note']} |"
        )
    return lines


def write_outputs(handoff_rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_execution_status_batch_handoff_completion_summary_handoff.csv"
    json_path = tables_dir / "meeteval_cpwer_execution_status_batch_handoff_completion_summary_handoff.json"
    md_path = figures_dir / "meeteval_cpwer_execution_status_batch_handoff_completion_summary_handoff.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HANDOFF_COLUMNS)
        writer.writeheader()
        writer.writerows(handoff_rows)
    json_path.write_text(json.dumps(handoff_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_handoff_lines(handoff_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    handoff_rows = build_handoff_rows(load_completion_summary())
    if not handoff_rows:
        print("Batch handoff completion summary not found; handoff not written.")
        return
    csv_path, json_path, md_path = write_outputs(handoff_rows)
    print(
        "Wrote MeetEval cpWER execution status batch handoff completion summary handoff CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER execution status batch handoff completion summary handoff JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER execution status batch handoff completion summary handoff note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
