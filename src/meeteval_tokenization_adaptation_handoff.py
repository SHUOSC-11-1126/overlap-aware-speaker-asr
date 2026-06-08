from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


HANDOFF_COLUMNS = [
    "handoff_status",
    "aligned_count",
    "total_count",
    "tokenization_queue_status",
    "handoff_target",
    "handoff_goal",
    "expected_evidence",
    "handoff_note",
]


def load_json_dict(path_rel: str) -> dict[str, str]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_handoff_row(completion_summary: dict[str, str]) -> dict[str, str]:
    aligned_count = str(completion_summary.get("aligned_count", "0"))
    total_count = str(completion_summary.get("total_count", "0"))
    queue_status = str(completion_summary.get("queue_status", "queue_in_progress"))
    ready = queue_status == "queue_complete" and int(aligned_count or 0) == int(total_count or 0)
    return {
        "handoff_status": "tokenization_adaptation_handoff_ready" if ready else "tokenization_adaptation_handoff_pending",
        "aligned_count": aligned_count,
        "total_count": total_count,
        "tokenization_queue_status": queue_status,
        "handoff_target": "results/figures/frontier_execution_receipt_fill_execution_operator_brief.md",
        "handoff_goal": (
            "Advance frontier fill execution after character-spaced cpWER reconciles with bridge-lite."
        ),
        "expected_evidence": "results/tables/frontier_execution_receipt_fill_execution_evidence_receipt.csv",
        "handoff_note": (
            "experimental/frontier tokenization adaptation handoff only; "
            "full MeetEval benchmark completion is not claimed."
        ),
    }


def build_handoff_lines(row: dict[str, str]) -> list[str]:
    return [
        "# MeetEval cpWER Tokenization Adaptation Handoff",
        "",
        "This generated handoff turns tokenization adaptation completion into a frontier fill execution action. "
        "It does not claim full MeetEval benchmark completion.",
        "",
        "| handoff_status | aligned_count | total_count | tokenization_queue_status | handoff_target | handoff_goal | expected_evidence | handoff_note |",
        "| --- | ---: | ---: | --- | --- | --- | --- | --- |",
        (
            f"| {row['handoff_status']} | {row['aligned_count']} | {row['total_count']} | "
            f"{row['tokenization_queue_status']} | {row['handoff_target']} | {row['handoff_goal']} | "
            f"{row['expected_evidence']} | {row['handoff_note']} |"
        ),
    ]


def write_outputs(handoff_row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_tokenization_adaptation_handoff.csv"
    json_path = tables_dir / "meeteval_tokenization_adaptation_handoff.json"
    md_path = figures_dir / "meeteval_tokenization_adaptation_handoff.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HANDOFF_COLUMNS)
        writer.writeheader()
        writer.writerow(handoff_row)
    json_path.write_text(json.dumps(handoff_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_handoff_lines(handoff_row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    completion_summary = load_json_dict(
        "results/tables/meeteval_cpwer_tokenization_adaptation_completion_summary.json"
    )
    if not completion_summary:
        print("Tokenization adaptation completion summary not found; handoff not written.")
        return
    handoff_row = build_handoff_row(completion_summary)
    csv_path, json_path, md_path = write_outputs(handoff_row)
    print(f"Wrote MeetEval tokenization adaptation handoff CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval tokenization adaptation handoff JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval tokenization adaptation handoff note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Handoff status: {handoff_row['handoff_status']}")


if __name__ == "__main__":
    main()
