from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


PASS_COLUMNS = [
    "case_id",
    "label",
    "review_priority",
    "risk_explanation",
    "candidate_repair",
    "uncertainty_note",
    "review_outcome",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "review_scope",
    "case_id",
    "review_outcome",
    "expected_inputs",
    "writeback_note",
]


def load_review_queue() -> list[dict[str, str]]:
    queue_path = PROJECT_ROOT / "results" / "tables" / "llm_critic_review_queue.csv"
    if not queue_path.exists():
        return []
    with queue_path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_qualitative_row(case_id: str) -> dict[str, str]:
    summary_path = PROJECT_ROOT / "results" / "tables" / "llm_critic_qualitative_summary.csv"
    if not summary_path.exists():
        return {}
    with summary_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if str(row.get("case_id", "")) == case_id:
                return row
    return {}


def select_queue_head(queue_rows: list[dict[str, str]]) -> dict[str, str]:
    if not queue_rows:
        return {"case_id": "HeavyOverlap"}
    return queue_rows[0]


def build_review_pass_row(queue_row: dict[str, str], qualitative_row: dict[str, str]) -> dict[str, str]:
    case_id = str(queue_row.get("case_id", qualitative_row.get("case_id", "HeavyOverlap")))
    candidate_repair = str(
        qualitative_row.get("candidate_repair", queue_row.get("candidate_repair", ""))
    )
    return {
        "case_id": case_id,
        "label": str(qualitative_row.get("label", "qualitative/demo")),
        "review_priority": str(queue_row.get("review_priority", "high")),
        "risk_explanation": str(qualitative_row.get("risk_explanation", "")),
        "candidate_repair": candidate_repair,
        "uncertainty_note": str(qualitative_row.get("uncertainty_note", "")),
        "review_outcome": (
            f"Qualitative critic pass recorded for {case_id}; no verified transcript repair was applied."
        ),
    }


def build_review_pass_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# LLM Critic Review Pass",
        "",
        "This generated note records the first qualitative critic-style review pass. "
        "It does not claim verified transcript correction.",
        "",
        "| case_id | label | review_priority | risk_explanation | candidate_repair | uncertainty_note | review_outcome |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['case_id']} | {row['label']} | {row['review_priority']} | {row['risk_explanation']} | "
            f"{row['candidate_repair']} | {row['uncertainty_note']} | {row['review_outcome']} |"
        ),
    ]
    return lines


def build_review_pass_receipt_rows(pass_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "review_complete",
            "review_scope": "single_verified_case",
            "case_id": str(pass_row.get("case_id", "")),
            "review_outcome": str(pass_row.get("review_outcome", "")),
            "expected_inputs": "Critic review queue head plus qualitative summary row.",
            "writeback_note": "Qualitative critic pass complete; no verified repair claim was made.",
        }
    ]


def build_review_pass_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# LLM Critic Review Receipt",
        "",
        "This receipt records the first qualitative critic pass writeback. It does not claim verified transcript correction.",
        "",
        "| execution_status | review_scope | case_id | review_outcome | expected_inputs | writeback_note |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['review_scope']} | {row['case_id']} | {row['review_outcome']} | "
            f"{row['expected_inputs']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    pass_row: dict[str, str],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    pass_csv_path = tables_dir / "llm_critic_review_pass.csv"
    pass_json_path = tables_dir / "llm_critic_review_pass.json"
    pass_md_path = figures_dir / "llm_critic_review_pass.md"
    receipt_json_path = tables_dir / "llm_critic_review_receipt.json"
    receipt_md_path = figures_dir / "llm_critic_review_receipt.md"

    with pass_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=PASS_COLUMNS)
        writer.writeheader()
        writer.writerow(pass_row)
    pass_json_path.write_text(json.dumps(pass_row, ensure_ascii=False, indent=2), encoding="utf-8")
    pass_md_path.write_text("\n".join(build_review_pass_lines(pass_row)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_review_pass_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return pass_csv_path, pass_json_path, pass_md_path, receipt_json_path, receipt_md_path


def main() -> None:
    queue_rows = load_review_queue()
    head = select_queue_head(queue_rows)
    case_id = str(head.get("case_id", "HeavyOverlap"))
    qualitative_row = load_qualitative_row(case_id)
    pass_row = build_review_pass_row(head, qualitative_row)
    receipt_rows = build_review_pass_receipt_rows(pass_row)
    pass_csv_path, pass_json_path, pass_md_path, receipt_json_path, receipt_md_path = write_outputs(
        pass_row,
        receipt_rows,
    )
    print(f"Wrote LLM critic review pass CSV: {pass_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass JSON: {pass_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass note: {pass_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review receipt JSON: {receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review receipt note: {receipt_md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
