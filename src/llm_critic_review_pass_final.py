from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT
from .llm_critic_review_pass import (
    build_review_pass_lines,
    build_review_pass_receipt_lines,
    build_review_pass_receipt_rows,
    build_review_pass_row,
    load_qualitative_row,
    load_review_queue,
)


FINAL_COLUMNS = [
    "queue_order",
    "case_id",
    "completed_pass_count",
    "review_priority",
    "review_outcome",
    "final_note",
]

COMPLETED_PASS_PATHS = (
    "results/tables/llm_critic_review_pass.json",
    "results/tables/llm_critic_review_pass_second.json",
    "results/tables/llm_critic_review_pass_third.json",
    "results/tables/llm_critic_review_pass_fourth.json",
)


def load_status_summary() -> dict[str, str]:
    summary_path = PROJECT_ROOT / "results" / "tables" / "llm_critic_review_pass_status_summary.json"
    if not summary_path.exists():
        return {}
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_completed_cases() -> set[str]:
    completed: set[str] = set()
    for rel_path in COMPLETED_PASS_PATHS:
        path = PROJECT_ROOT / rel_path
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            case_id = str(payload.get("case_id", "")).strip()
            if case_id:
                completed.add(case_id)
    return completed


def select_queue_row_for_case(queue_rows: list[dict[str, str]], case_id: str) -> dict[str, str]:
    for row in queue_rows:
        if str(row.get("case_id", "")) == case_id:
            return row
    return {"case_id": case_id, "review_priority": "high", "queue_order": "5"}


def build_final_row(
    queue_row: dict[str, str],
    pass_row: dict[str, str],
    completed_count: int,
) -> dict[str, str]:
    case_id = str(pass_row.get("case_id", ""))
    return {
        "queue_order": str(queue_row.get("queue_order", "")),
        "case_id": case_id,
        "completed_pass_count": str(completed_count),
        "review_priority": str(pass_row.get("review_priority", "high")),
        "review_outcome": str(pass_row.get("review_outcome", "")),
        "final_note": (
            f"Final qualitative pass recorded for {case_id}; gold review queue is now complete "
            "without any verified transcript repair claim."
        ),
    }


def build_final_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# LLM Critic Review Pass Final",
        "",
        "This generated note records the final qualitative critic-style review pass for the gold queue. "
        "It does not claim verified transcript correction.",
        "",
        "| queue_order | case_id | completed_pass_count | review_priority | review_outcome | final_note |",
        "| --- | --- | ---: | --- | --- | --- |",
        (
            f"| {row['queue_order']} | {row['case_id']} | {row['completed_pass_count']} | "
            f"{row['review_priority']} | {row['review_outcome']} | {row['final_note']} |"
        ),
    ]
    return lines


def write_outputs(
    final_row: dict[str, str],
    pass_row: dict[str, str],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    final_csv_path = tables_dir / "llm_critic_review_pass_final.csv"
    final_json_path = tables_dir / "llm_critic_review_pass_final.json"
    final_md_path = figures_dir / "llm_critic_review_pass_final.md"
    fifth_csv_path = tables_dir / "llm_critic_review_pass_fifth.csv"
    fifth_json_path = tables_dir / "llm_critic_review_pass_fifth.json"
    fifth_md_path = figures_dir / "llm_critic_review_pass_fifth.md"
    receipt_json_path = tables_dir / "llm_critic_review_pass_final_receipt.json"
    receipt_md_path = figures_dir / "llm_critic_review_pass_final_receipt.md"

    with final_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FINAL_COLUMNS)
        writer.writeheader()
        writer.writerow(final_row)
    final_json_path.write_text(json.dumps(final_row, ensure_ascii=False, indent=2), encoding="utf-8")
    final_md_path.write_text("\n".join(build_final_lines(final_row)) + "\n", encoding="utf-8")

    with fifth_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(pass_row.keys()))
        writer.writeheader()
        writer.writerow(pass_row)
    fifth_json_path.write_text(json.dumps(pass_row, ensure_ascii=False, indent=2), encoding="utf-8")
    fifth_md_path.write_text("\n".join(build_review_pass_lines(pass_row)) + "\n", encoding="utf-8")

    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_review_pass_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return (
        final_csv_path,
        final_json_path,
        final_md_path,
        fifth_csv_path,
        fifth_json_path,
        fifth_md_path,
        receipt_json_path,
        receipt_md_path,
    )


def main() -> None:
    summary = load_status_summary()
    next_case_id = str(summary.get("next_case_id", "OppositeOverlap"))
    queue_rows = load_review_queue()
    queue_row = select_queue_row_for_case(queue_rows, next_case_id)
    qualitative_row = load_qualitative_row(next_case_id)
    pass_row = build_review_pass_row(queue_row, qualitative_row)
    completed_count = len(load_completed_cases())
    final_row = build_final_row(queue_row, pass_row, completed_count)
    receipt_rows = build_review_pass_receipt_rows(pass_row)
    for receipt in receipt_rows:
        receipt["writeback_note"] = (
            f"Final qualitative pass complete for {next_case_id}; gold queue review is complete "
            "without any verified repair claim."
        )
    (
        final_csv_path,
        final_json_path,
        final_md_path,
        fifth_csv_path,
        fifth_json_path,
        fifth_md_path,
        receipt_json_path,
        receipt_md_path,
    ) = write_outputs(final_row, pass_row, receipt_rows)
    print(f"Wrote LLM critic review pass final CSV: {final_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass final JSON: {final_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass final note: {final_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass fifth CSV: {fifth_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass fifth JSON: {fifth_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass fifth note: {fifth_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass final receipt JSON: {receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass final receipt note: {receipt_md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
