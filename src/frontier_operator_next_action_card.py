from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


ACTION_COLUMNS = [
    "action_lane",
    "frontier_name",
    "go_no_go_state",
    "current_state",
    "operator_action",
    "prerequisite_artifact",
    "target_artifact",
    "action_boundary",
]

SUMMARY_COLUMNS = [
    "scope",
    "coordination_state",
    "ready_frontier",
    "blocked_frontier",
    "ready_action_lane",
    "blocked_action_lane",
    "operator_sequence",
    "observation",
]

TARGET_ARTIFACTS = {
    "meeteval_compatibility": "results/tables/meeteval_cpwer_execution_receipt.json",
    "external_validation": "results/tables/external_validation_license_confirmation_receipt_bridge.json",
    "speaker_profile": "results/tables/speaker_profile_embedding_trial_execution_receipt.json",
    "llm_critic": "results/tables/llm_critic_review_receipt.json",
    "demo_excellence": "results/tables/demo_walkthrough_receipt.json",
}


def load_json_payload(path_rel: str) -> dict | list:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, (dict, list)) else {}


def _row_by_name(board_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {str(row.get("frontier_name", "")): row for row in board_rows}


def _build_lane_row(action_lane: str, frontier_name: str, frontier_row: dict[str, str]) -> dict[str, str]:
    return {
        "action_lane": action_lane,
        "frontier_name": frontier_name,
        "go_no_go_state": str(frontier_row.get("go_no_go_state", "")),
        "current_state": str(frontier_row.get("current_state", "")),
        "operator_action": str(frontier_row.get("recommended_next_action", "")),
        "prerequisite_artifact": str(frontier_row.get("evidence_artifact", "")),
        "target_artifact": TARGET_ARTIFACTS.get(frontier_name, ""),
        "action_boundary": str(frontier_row.get("primary_boundary", "")),
    }


def build_action_rows(
    board_rows: list[dict[str, str]],
    go_no_go_summary: dict[str, str],
) -> list[dict[str, str]]:
    rows_by_name = _row_by_name(board_rows)
    rows: list[dict[str, str]] = []

    ready_frontier = str(go_no_go_summary.get("highest_priority_ready_frontier", ""))
    if ready_frontier and ready_frontier in rows_by_name:
        rows.append(_build_lane_row("ready_lane", ready_frontier, rows_by_name[ready_frontier]))

    blocked_frontier = str(go_no_go_summary.get("highest_priority_blocked_frontier", ""))
    if blocked_frontier and blocked_frontier in rows_by_name:
        rows.append(_build_lane_row("blocked_lane", blocked_frontier, rows_by_name[blocked_frontier]))

    return rows


def build_summary_row(
    action_rows: list[dict[str, str]],
    go_no_go_summary: dict[str, str],
) -> dict[str, str]:
    ready_frontier = str(go_no_go_summary.get("highest_priority_ready_frontier", ""))
    blocked_frontier = str(go_no_go_summary.get("highest_priority_blocked_frontier", ""))
    lanes = [f"{row.get('action_lane', '')}:{row.get('frontier_name', '')}" for row in action_rows]
    return {
        "scope": "frontier_operator_next_action_card",
        "coordination_state": str(go_no_go_summary.get("coordination_state", "")),
        "ready_frontier": ready_frontier,
        "blocked_frontier": blocked_frontier,
        "ready_action_lane": "ready_lane" if ready_frontier else "",
        "blocked_action_lane": "blocked_lane" if blocked_frontier else "",
        "operator_sequence": " -> ".join(lanes),
        "observation": (
            "Operator card only; it converts top-level frontier readiness into the next coordination actions "
            "without claiming experiment completion."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Operator Next-Action Card",
        "",
        "This generated card converts the unified frontier go/no-go board into explicit next actions. "
        "It remains coordination-only and does not claim that any frontier result has been achieved.",
        "",
        "| action_lane | frontier_name | go_no_go_state | current_state | operator_action | prerequisite_artifact | target_artifact | action_boundary |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['action_lane']} | {row['frontier_name']} | {row['go_no_go_state']} | "
            f"{row['current_state']} | {row['operator_action']} | {row['prerequisite_artifact']} | "
            f"{row['target_artifact']} | {row['action_boundary']} |"
        )
    return lines


def build_summary_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Frontier Operator Next-Action Summary",
        "",
        "This generated summary condenses the operator card into one ordered coordination sequence.",
        "",
        "| scope | coordination_state | ready_frontier | blocked_frontier | ready_action_lane | blocked_action_lane | operator_sequence | observation |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['scope']} | {row['coordination_state']} | {row['ready_frontier']} | "
            f"{row['blocked_frontier']} | {row['ready_action_lane']} | {row['blocked_action_lane']} | "
            f"{row['operator_sequence']} | {row['observation']} |"
        ),
    ]


def write_outputs(
    action_rows: list[dict[str, str]],
    summary_row: dict[str, str],
) -> tuple[Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    card_csv = tables_dir / "frontier_operator_next_action_card.csv"
    card_json = tables_dir / "frontier_operator_next_action_card.json"
    summary_csv = tables_dir / "frontier_operator_next_action_summary.csv"
    summary_json = tables_dir / "frontier_operator_next_action_summary.json"
    card_md = figures_dir / "frontier_operator_next_action_card.md"
    summary_md = figures_dir / "frontier_operator_next_action_summary.md"

    with card_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=ACTION_COLUMNS)
        writer.writeheader()
        writer.writerows(action_rows)
    card_json.write_text(json.dumps(action_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    with summary_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerow(summary_row)
    summary_json.write_text(json.dumps(summary_row, ensure_ascii=False, indent=2), encoding="utf-8")

    card_md.write_text("\n".join(build_card_lines(action_rows)) + "\n", encoding="utf-8")
    summary_md.write_text("\n".join(build_summary_lines(summary_row)) + "\n", encoding="utf-8")
    return card_csv, card_json, summary_csv, summary_json, card_md, summary_md


def main() -> None:
    board_rows = load_json_payload("results/tables/frontier_go_no_go_board.json")
    go_no_go_summary = load_json_payload("results/tables/frontier_go_no_go_summary.json")
    board_rows_list = board_rows if isinstance(board_rows, list) else []
    summary_dict = go_no_go_summary if isinstance(go_no_go_summary, dict) else {}
    action_rows = build_action_rows(board_rows_list, summary_dict)
    summary_row = build_summary_row(action_rows, summary_dict)
    outputs = write_outputs(action_rows, summary_row)
    print(f"Wrote frontier operator next-action card CSV: {outputs[0].relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier operator next-action card JSON: {outputs[1].relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier operator next-action summary CSV: {outputs[2].relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier operator next-action summary JSON: {outputs[3].relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier operator next-action note: {outputs[4].relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier operator next-action summary note: {outputs[5].relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
