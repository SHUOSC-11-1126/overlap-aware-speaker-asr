from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT
from .llm_critic_review_pass_status import (
    build_status_lines,
    build_status_rows,
    build_summary_row,
    load_completed_cases,
    load_review_queue,
)


COMPLETION_COLUMNS = [
    "scope",
    "completed_count",
    "pending_count",
    "queue_status",
    "observation",
]


def build_completion_summary_row(status_rows: list[dict[str, str]]) -> dict[str, str]:
    summary = build_summary_row(status_rows)
    pending_count = int(summary.get("pending_count", 0) or 0)
    queue_status = "queue_complete" if pending_count == 0 else "queue_in_progress"
    return {
        "scope": str(summary.get("scope", "gold_review_queue")),
        "completed_count": str(summary.get("completed_count", "0")),
        "pending_count": str(summary.get("pending_count", "0")),
        "queue_status": queue_status,
        "observation": (
            "Qualitative/demo gold review queue completion rollup; no verified transcript repair is claimed."
        ),
    }


def build_completion_summary_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# LLM Critic Review Pass Completion Summary",
        "",
        "This generated note summarizes gold-queue completion for the qualitative critic pass layer. "
        "It does not claim verified transcript correction.",
        "",
        "| scope | completed_count | pending_count | queue_status | observation |",
        "| --- | ---: | ---: | --- | --- |",
        (
            f"| {row['scope']} | {row['completed_count']} | {row['pending_count']} | "
            f"{row['queue_status']} | {row['observation']} |"
        ),
    ]
    return lines


def write_outputs(
    status_rows: list[dict[str, str]],
    completion_row: dict[str, str],
) -> tuple[Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    status_csv_path = tables_dir / "llm_critic_review_pass_status.csv"
    status_json_path = tables_dir / "llm_critic_review_pass_status.json"
    status_md_path = figures_dir / "llm_critic_review_pass_status.md"
    completion_csv_path = tables_dir / "llm_critic_review_pass_completion_summary.csv"
    completion_json_path = tables_dir / "llm_critic_review_pass_completion_summary.json"
    completion_md_path = figures_dir / "llm_critic_review_pass_completion_summary.md"

    with status_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(status_rows[0].keys()) if status_rows else [])
        if status_rows:
            writer.writeheader()
            writer.writerows(status_rows)
    status_json_path.write_text(json.dumps(status_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    status_md_path.write_text("\n".join(build_status_lines(status_rows)) + "\n", encoding="utf-8")

    with completion_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COMPLETION_COLUMNS)
        writer.writeheader()
        writer.writerow(completion_row)
    completion_json_path.write_text(json.dumps(completion_row, ensure_ascii=False, indent=2), encoding="utf-8")
    completion_md_path.write_text(
        "\n".join(build_completion_summary_lines(completion_row)) + "\n",
        encoding="utf-8",
    )
    return (
        status_csv_path,
        status_json_path,
        status_md_path,
        completion_csv_path,
        completion_json_path,
        completion_md_path,
    )


def main() -> None:
    queue_rows = load_review_queue()
    completed_cases = load_completed_cases()
    status_rows = build_status_rows(queue_rows, completed_cases)
    completion_row = build_completion_summary_row(status_rows)
    (
        status_csv_path,
        status_json_path,
        status_md_path,
        completion_csv_path,
        completion_json_path,
        completion_md_path,
    ) = write_outputs(status_rows, completion_row)
    print(f"Wrote LLM critic review pass status CSV: {status_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass status JSON: {status_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass status note: {status_md_path.relative_to(PROJECT_ROOT)}")
    print(
        "Wrote LLM critic review pass completion summary CSV: "
        f"{completion_csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote LLM critic review pass completion summary JSON: "
        f"{completion_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote LLM critic review pass completion summary note: "
        f"{completion_md_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Completion summary: "
        f"completed={completion_row['completed_count']}, pending={completion_row['pending_count']}, "
        f"queue_status={completion_row['queue_status']}"
    )


if __name__ == "__main__":
    main()
