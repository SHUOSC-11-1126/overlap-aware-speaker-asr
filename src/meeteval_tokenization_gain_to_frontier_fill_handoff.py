from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


HANDOFF_COLUMNS = [
    "handoff_status",
    "queue_status",
    "adapted_and_aligned_count",
    "case_count",
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
        / "meeteval_cpwer_tokenization_gain_scorecard_handoff_completion_summary.json"
    )
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_handoff_row(summary: dict[str, str]) -> dict[str, str]:
    queue_status = str(summary.get("queue_status", "queue_in_progress"))
    handoff_status = str(summary.get("handoff_status", "tokenization_gain_handoff_pending"))
    adapted_and_aligned_count = str(summary.get("adapted_and_aligned_count", "0"))
    case_count = str(summary.get("case_count", "0"))
    ready = queue_status == "queue_complete" and handoff_status == "tokenization_gain_handoff_ready"
    return {
        "handoff_status": "tokenization_gain_frontier_fill_handoff_ready" if ready else "tokenization_gain_frontier_fill_handoff_pending",
        "queue_status": queue_status,
        "adapted_and_aligned_count": adapted_and_aligned_count,
        "case_count": case_count,
        "handoff_target": "results/figures/frontier_execution_receipt_fill_execution_runbook_card.md",
        "handoff_goal": (
            "Advance frontier fill execution after tokenization gain handoff completion confirms character-spaced cpWER."
        ),
        "expected_evidence": "results/tables/frontier_execution_receipt_fill_execution_runbook_card.csv",
        "handoff_note": (
            "experimental/frontier tokenization-to-fill handoff only; "
            "full MeetEval benchmark completion is not claimed."
        ),
    }


def build_handoff_lines(row: dict[str, str]) -> list[str]:
    return [
        "# MeetEval Tokenization Gain To Frontier Fill Handoff",
        "",
        "This generated handoff connects tokenization gain handoff completion to the frontier fill runbook card. "
        "It does not claim full MeetEval benchmark completion.",
        "",
        "| handoff_status | queue_status | adapted_and_aligned_count | case_count | handoff_target | handoff_goal | expected_evidence | handoff_note |",
        "| --- | --- | ---: | ---: | --- | --- | --- | --- |",
        (
            f"| {row['handoff_status']} | {row['queue_status']} | {row['adapted_and_aligned_count']} | "
            f"{row['case_count']} | {row['handoff_target']} | {row['handoff_goal']} | "
            f"{row['expected_evidence']} | {row['handoff_note']} |"
        ),
    ]


def write_outputs(handoff_row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_tokenization_gain_to_frontier_fill_handoff.csv"
    json_path = tables_dir / "meeteval_tokenization_gain_to_frontier_fill_handoff.json"
    md_path = figures_dir / "meeteval_tokenization_gain_to_frontier_fill_handoff.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HANDOFF_COLUMNS)
        writer.writeheader()
        writer.writerow(handoff_row)
    json_path.write_text(json.dumps(handoff_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_handoff_lines(handoff_row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    summary = load_completion_summary()
    if not summary:
        print("Tokenization gain handoff completion summary not found; frontier fill handoff not written.")
        return
    handoff_row = build_handoff_row(summary)
    csv_path, json_path, md_path = write_outputs(handoff_row)
    print(f"Wrote MeetEval tokenization gain to frontier fill handoff CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval tokenization gain to frontier fill handoff JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval tokenization gain to frontier fill handoff note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Handoff status: {handoff_row['handoff_status']}")


if __name__ == "__main__":
    main()
