from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


STATUS_COLUMNS = [
    "queue_order",
    "case_id",
    "pass_status",
    "review_priority",
    "next_action",
]

SUMMARY_COLUMNS = [
    "scope",
    "completed_count",
    "pending_count",
    "next_case_id",
    "observation",
]


def load_review_queue() -> list[dict[str, str]]:
    queue_path = PROJECT_ROOT / "results" / "tables" / "llm_critic_review_queue.csv"
    if not queue_path.exists():
        return []
    with queue_path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_completed_cases() -> set[str]:
    completed: set[str] = set()
    for rel_path in (
        "results/tables/llm_critic_review_pass.json",
        "results/tables/llm_critic_review_pass_second.json",
        "results/tables/llm_critic_review_pass_third.json",
        "results/tables/llm_critic_review_pass_fourth.json",
    ):
        path = PROJECT_ROOT / rel_path
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            case_id = str(payload.get("case_id", "")).strip()
            if case_id:
                completed.add(case_id)
    return completed


def build_status_rows(
    queue_rows: list[dict[str, str]],
    completed_cases: set[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for queue_row in queue_rows:
        case_id = str(queue_row.get("case_id", ""))
        pass_status = "review_complete" if case_id in completed_cases else "pending_review"
        next_action = (
            "Continue qualitative review without claiming verified repair."
            if pass_status == "pending_review"
            else "Pass recorded; move to the next queue item when ready."
        )
        rows.append(
            {
                "queue_order": str(queue_row.get("queue_order", "")),
                "case_id": case_id,
                "pass_status": pass_status,
                "review_priority": str(queue_row.get("review_priority", "high")),
                "next_action": next_action,
            }
        )
    return rows


def build_summary_row(status_rows: list[dict[str, str]]) -> dict[str, str]:
    completed_count = sum(1 for row in status_rows if row["pass_status"] == "review_complete")
    pending_rows = [row for row in status_rows if row["pass_status"] == "pending_review"]
    next_case_id = pending_rows[0]["case_id"] if pending_rows else ""
    return {
        "scope": "gold_review_queue",
        "completed_count": str(completed_count),
        "pending_count": str(len(pending_rows)),
        "next_case_id": next_case_id,
        "observation": (
            "Qualitative/demo queue status rollup; no verified transcript repair is claimed for completed passes."
        ),
    }


def build_status_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# LLM Critic Review Pass Status",
        "",
        "This generated note rolls up qualitative critic pass status across the gold review queue. "
        "It does not claim verified transcript correction.",
        "",
        "| queue_order | case_id | pass_status | review_priority | next_action |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['queue_order']} | {row['case_id']} | {row['pass_status']} | "
            f"{row['review_priority']} | {row['next_action']} |"
        )
    return lines


def build_summary_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# LLM Critic Review Pass Status Summary",
        "",
        "This generated note summarizes queue completion for the qualitative critic pass layer.",
        "",
        "| scope | completed_count | pending_count | next_case_id | observation |",
        "| --- | ---: | ---: | --- | --- |",
        (
            f"| {row['scope']} | {row['completed_count']} | {row['pending_count']} | "
            f"{row['next_case_id']} | {row['observation']} |"
        ),
    ]
    return lines


def write_outputs(
    status_rows: list[dict[str, str]],
    summary_row: dict[str, str],
) -> tuple[Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    status_csv_path = tables_dir / "llm_critic_review_pass_status.csv"
    status_json_path = tables_dir / "llm_critic_review_pass_status.json"
    status_md_path = figures_dir / "llm_critic_review_pass_status.md"
    summary_csv_path = tables_dir / "llm_critic_review_pass_status_summary.csv"
    summary_json_path = tables_dir / "llm_critic_review_pass_status_summary.json"
    summary_md_path = figures_dir / "llm_critic_review_pass_status_summary.md"

    with status_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=STATUS_COLUMNS)
        writer.writeheader()
        writer.writerows(status_rows)
    status_json_path.write_text(json.dumps(status_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    status_md_path.write_text("\n".join(build_status_lines(status_rows)) + "\n", encoding="utf-8")
    with summary_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerow(summary_row)
    summary_json_path.write_text(json.dumps(summary_row, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_md_path.write_text("\n".join(build_summary_lines(summary_row)) + "\n", encoding="utf-8")
    return (
        status_csv_path,
        status_json_path,
        status_md_path,
        summary_csv_path,
        summary_json_path,
        summary_md_path,
    )


def main() -> None:
    queue_rows = load_review_queue()
    completed_cases = load_completed_cases()
    status_rows = build_status_rows(queue_rows, completed_cases)
    summary_row = build_summary_row(status_rows)
    (
        status_csv_path,
        status_json_path,
        status_md_path,
        summary_csv_path,
        summary_json_path,
        summary_md_path,
    ) = write_outputs(status_rows, summary_row)
    print(f"Wrote LLM critic review pass status CSV: {status_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass status JSON: {status_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass status note: {status_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass status summary CSV: {summary_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass status summary JSON: {summary_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass status summary note: {summary_md_path.relative_to(PROJECT_ROOT)}")
    print(
        "Status summary: "
        f"completed={summary_row['completed_count']}, pending={summary_row['pending_count']}, "
        f"next_case_id={summary_row['next_case_id']}"
    )


if __name__ == "__main__":
    main()
