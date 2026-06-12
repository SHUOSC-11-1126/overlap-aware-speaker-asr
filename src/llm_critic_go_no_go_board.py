from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BOARD_COLUMNS = [
    "checkpoint_name",
    "scope",
    "current_status",
    "claim_boundary",
    "go_no_go_state",
    "next_action",
    "evidence_artifact",
]

SUMMARY_COLUMNS = [
    "scope",
    "checkpoint_count",
    "go_count",
    "no_go_count",
    "overall_state",
    "primary_boundary",
    "recommended_next_action",
    "observation",
]


def load_json_payload(path_rel: str) -> dict | list:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, (dict, list)) else {}


def load_csv_rows(path_rel: str) -> list[dict[str, str]]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{key: str(value) for key, value in row.items()} for row in csv.DictReader(f)]


def classify_go_no_go_state(current_status: str) -> str:
    lowered = current_status.strip().lower()
    if lowered in {"queue_complete", "review_complete"}:
        return "go"
    return "no_go"


def build_checkpoint_rows() -> list[dict[str, str]]:
    qualitative_rows = load_csv_rows("results/tables/llm_critic_qualitative_summary.csv")
    queue_rows = load_csv_rows("results/tables/llm_critic_review_queue.csv")
    status = load_json_payload("results/tables/llm_critic_review_pass_status.json")
    completion = load_json_payload("results/tables/llm_critic_review_pass_completion_summary.json")
    receipt = load_json_payload("results/tables/llm_critic_review_receipt.json")

    first_case = queue_rows[0]["case_id"] if queue_rows else "HeavyOverlap"
    qualitative_status = "review_complete" if qualitative_rows else "missing"
    queue_status = "queue_complete" if queue_rows else "missing"
    if isinstance(status, list):
        completed_flags = [str(row.get("pass_status", "")) == "review_complete" for row in status if isinstance(row, dict)]
        status_queue = "queue_complete" if completed_flags and all(completed_flags) else "queue_in_progress"
    else:
        status_queue = str((status if isinstance(status, dict) else {}).get("queue_status", ""))
    completion_status = str((completion if isinstance(completion, dict) else {}).get("queue_status", ""))
    receipt_status = (
        str((receipt[0] if isinstance(receipt, list) and receipt else {}).get("execution_status", ""))
        if isinstance(receipt, list)
        else str((receipt if isinstance(receipt, dict) else {}).get("execution_status", ""))
    )

    return [
        {
            "checkpoint_name": "qualitative_critic_note",
            "scope": "gold_queue",
            "current_status": qualitative_status,
            "claim_boundary": "qualitative_only_not_verified_repair",
            "go_no_go_state": classify_go_no_go_state(qualitative_status),
            "next_action": "Treat the qualitative critic note as prioritization context, not as verified correction.",
            "evidence_artifact": "results/figures/llm_critic_qualitative_note.md",
        },
        {
            "checkpoint_name": "review_queue",
            "scope": f"gold_queue_first_case={first_case}",
            "current_status": queue_status,
            "claim_boundary": "queue_ready_not_repair_ready",
            "go_no_go_state": classify_go_no_go_state(queue_status),
            "next_action": "Use the queue only to order narrow qualitative writebacks.",
            "evidence_artifact": "results/figures/llm_critic_review_queue.md",
        },
        {
            "checkpoint_name": "review_status_rollup",
            "scope": "gold_queue",
            "current_status": status_queue,
            "claim_boundary": "queue_complete_not_verified_fix",
            "go_no_go_state": classify_go_no_go_state(status_queue),
            "next_action": "Use queue completion as evidence that qualitative coverage is done, not that repair is verified.",
            "evidence_artifact": "results/figures/llm_critic_review_pass_status.md",
        },
        {
            "checkpoint_name": "completion_summary",
            "scope": "gold_queue",
            "current_status": completion_status,
            "claim_boundary": "completion_ready_for_writeback_only",
            "go_no_go_state": classify_go_no_go_state(completion_status),
            "next_action": "If a next step is taken, keep it to a narrow qualitative writeback.",
            "evidence_artifact": "results/figures/llm_critic_review_pass_completion_summary.md",
        },
        {
            "checkpoint_name": "review_receipt",
            "scope": "single_qualitative_pass",
            "current_status": receipt_status,
            "claim_boundary": "receipt_template_only_blocks_verified_claims",
            "go_no_go_state": classify_go_no_go_state(receipt_status),
            "next_action": "Do not claim verified repair until a real writeback fills the receipt with checked evidence.",
            "evidence_artifact": "results/figures/llm_critic_review_receipt.md",
        },
    ]


def build_summary_row(rows: list[dict[str, str]]) -> dict[str, str]:
    go_count = sum(1 for row in rows if row.get("go_no_go_state") == "go")
    no_go_count = len(rows) - go_count
    narrow_coord_path = PROJECT_ROOT / "results/tables/llm_critic_narrow_dry_run_coordination_receipt.json"
    narrow_coord_complete = False
    if narrow_coord_path.exists():
        payload = json.loads(narrow_coord_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            narrow_coord_complete = (
                str(payload.get("execution_status", "")) == "llm_critic_narrow_dry_run_coordination_complete"
            )
    if rows and go_count == len(rows) and narrow_coord_complete:
        overall_state = "llm_critic_narrow_dry_run_coordination_complete"
    elif go_count >= 4:
        overall_state = "qualitative_writeback_ready"
    else:
        overall_state = "writeback_not_ready"
    return {
        "scope": "llm_critic_go_no_go_board",
        "checkpoint_count": str(len(rows)),
        "go_count": str(go_count),
        "no_go_count": str(no_go_count),
        "overall_state": overall_state,
        "primary_boundary": "verified_repair_claims_still_blocked",
        "recommended_next_action": (
            "Proceed only with a narrow qualitative writeback or repair mockup; "
            "do not claim verified transcript correction without filled evidence receipts."
        ),
        "observation": (
            "qualitative/demo coordination board only; it separates qualitative coverage readiness "
            "from blocked verified-repair claims."
        ),
    }


def build_board_lines(rows: list[dict[str, str]]) -> list[str]:
    go_count = sum(1 for row in rows if row.get("go_no_go_state") == "go")
    lines = [
        "# LLM Critic Go-No-Go Board",
        "",
        "This generated board compresses the current LLM-critic chain into a go/no-go view. "
        "It remains qualitative/demo and does not claim verified transcript correction.",
        "",
        f"Summary: `{go_count}/{len(rows)}` checkpoints are ready for a narrow qualitative writeback path, while verified repair claims remain blocked.",
        "",
        "| checkpoint_name | scope | current_status | claim_boundary | go_no_go_state | next_action | evidence_artifact |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checkpoint_name']} | {row['scope']} | {row['current_status']} | {row['claim_boundary']} | "
            f"{row['go_no_go_state']} | {row['next_action']} | {row['evidence_artifact']} |"
        )
    return lines


def build_summary_lines(row: dict[str, str]) -> list[str]:
    return [
        "# LLM Critic Go-No-Go Summary",
        "",
        "This generated summary condenses the LLM-critic decision board into one frontier action line. "
        "It remains qualitative/demo and does not claim verified transcript repair.",
        "",
        "| scope | checkpoint_count | go_count | no_go_count | overall_state | primary_boundary | recommended_next_action | observation |",
        "| --- | ---: | ---: | ---: | --- | --- | --- | --- |",
        (
            f"| {row['scope']} | {row['checkpoint_count']} | {row['go_count']} | {row['no_go_count']} | "
            f"{row['overall_state']} | {row['primary_boundary']} | {row['recommended_next_action']} | {row['observation']} |"
        ),
    ]


def write_outputs(
    rows: list[dict[str, str]],
    summary_row: dict[str, str],
) -> tuple[Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    board_csv = tables_dir / "llm_critic_go_no_go_board.csv"
    board_json = tables_dir / "llm_critic_go_no_go_board.json"
    summary_csv = tables_dir / "llm_critic_go_no_go_summary.csv"
    summary_json = tables_dir / "llm_critic_go_no_go_summary.json"
    board_md = figures_dir / "llm_critic_go_no_go_board.md"
    summary_md = figures_dir / "llm_critic_go_no_go_summary.md"

    with board_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BOARD_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    board_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    with summary_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerow(summary_row)
    summary_json.write_text(json.dumps(summary_row, ensure_ascii=False, indent=2), encoding="utf-8")

    board_md.write_text("\n".join(build_board_lines(rows)) + "\n", encoding="utf-8")
    summary_md.write_text("\n".join(build_summary_lines(summary_row)) + "\n", encoding="utf-8")
    return board_csv, board_json, summary_csv, summary_json, board_md, summary_md


def main() -> None:
    rows = build_checkpoint_rows()
    summary_row = build_summary_row(rows)
    outputs = write_outputs(rows, summary_row)
    print(f"Wrote LLM critic go-no-go board CSV: {outputs[0].relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic go-no-go board JSON: {outputs[1].relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic go-no-go summary CSV: {outputs[2].relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic go-no-go summary JSON: {outputs[3].relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic go-no-go board note: {outputs[4].relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic go-no-go summary note: {outputs[5].relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
