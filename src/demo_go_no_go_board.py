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


def classify_go_no_go_state(current_status: str) -> str:
    lowered = current_status.strip().lower()
    if lowered in {
        "queue_complete",
        "review_complete",
        "presentation_writeback_complete",
        "wave5_presentation_extension_complete",
        "wave6_presentation_extension_complete",
        "wave7_presentation_extension_complete",
    }:
        return "go"
    return "no_go"


def _receipt_status(payload: dict | list) -> str:
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            return str(first.get("execution_status", ""))
    if isinstance(payload, dict):
        return str(payload.get("execution_status", ""))
    return ""


def build_checkpoint_rows() -> list[dict[str, str]]:
    storyboard_receipt = load_json_payload("results/tables/demo_storyboard_receipt.json")
    storyboard_status = load_json_payload("results/tables/demo_storyboard_review_pass_status.json")
    storyboard_completion = load_json_payload("results/tables/demo_storyboard_review_pass_completion_summary.json")
    walkthrough_receipt = load_json_payload("results/tables/demo_walkthrough_receipt.json")
    walkthrough_status = load_json_payload("results/tables/demo_walkthrough_review_pass_status.json")
    walkthrough_completion = load_json_payload("results/tables/demo_walkthrough_review_pass_completion_summary.json")

    return [
        {
            "checkpoint_name": "storyboard_review_status",
            "scope": "storyboard_queue",
            "current_status": str((storyboard_status if isinstance(storyboard_status, dict) else {}).get("queue_status", "")),
            "claim_boundary": "storyboard_ready_not_live_delivery",
            "go_no_go_state": classify_go_no_go_state(str((storyboard_status if isinstance(storyboard_status, dict) else {}).get("queue_status", ""))),
            "next_action": "Use storyboard completion as support for a narrow presentation writeback, not as live demo proof.",
            "evidence_artifact": "results/figures/demo_storyboard_review_pass_status.md",
        },
        {
            "checkpoint_name": "storyboard_completion",
            "scope": "storyboard_queue",
            "current_status": str((storyboard_completion if isinstance(storyboard_completion, dict) else {}).get("queue_status", "")),
            "claim_boundary": "storyboard_completion_not_live_delivery",
            "go_no_go_state": classify_go_no_go_state(str((storyboard_completion if isinstance(storyboard_completion, dict) else {}).get("queue_status", ""))),
            "next_action": "If a next step is taken, keep it to a narrow storyboard writeback or polish pass.",
            "evidence_artifact": "results/figures/demo_storyboard_review_pass_completion_summary.md",
        },
        {
            "checkpoint_name": "walkthrough_review_status",
            "scope": "walkthrough_queue",
            "current_status": str((walkthrough_status if isinstance(walkthrough_status, dict) else {}).get("queue_status", "")),
            "claim_boundary": "walkthrough_ready_not_live_delivery",
            "go_no_go_state": classify_go_no_go_state(str((walkthrough_status if isinstance(walkthrough_status, dict) else {}).get("queue_status", ""))),
            "next_action": "Use walkthrough completion as support for a narrow presentation writeback, not as live demo proof.",
            "evidence_artifact": "results/figures/demo_walkthrough_review_pass_status.md",
        },
        {
            "checkpoint_name": "walkthrough_completion",
            "scope": "walkthrough_queue",
            "current_status": str((walkthrough_completion if isinstance(walkthrough_completion, dict) else {}).get("queue_status", "")),
            "claim_boundary": "walkthrough_completion_not_live_delivery",
            "go_no_go_state": classify_go_no_go_state(str((walkthrough_completion if isinstance(walkthrough_completion, dict) else {}).get("queue_status", ""))),
            "next_action": "If a next step is taken, keep it to a narrow walkthrough writeback or delivery mockup.",
            "evidence_artifact": "results/figures/demo_walkthrough_review_pass_completion_summary.md",
        },
        {
            "checkpoint_name": "storyboard_receipt",
            "scope": "single_storyboard_writeback",
            "current_status": _receipt_status(storyboard_receipt),
            "claim_boundary": "receipt_template_only_blocks_live_claims",
            "go_no_go_state": classify_go_no_go_state(_receipt_status(storyboard_receipt)),
            "next_action": "Do not claim live delivery until a real storyboard writeback fills the receipt with evidence.",
            "evidence_artifact": "results/figures/demo_storyboard_receipt.md",
        },
        {
            "checkpoint_name": "walkthrough_receipt",
            "scope": "single_walkthrough_writeback",
            "current_status": _receipt_status(walkthrough_receipt),
            "claim_boundary": "receipt_template_only_blocks_live_claims",
            "go_no_go_state": classify_go_no_go_state(_receipt_status(walkthrough_receipt)),
            "next_action": "Do not claim live delivery until a real walkthrough writeback fills the receipt with evidence.",
            "evidence_artifact": "results/figures/demo_walkthrough_receipt.md",
        },
    ]


def build_summary_row(rows: list[dict[str, str]]) -> dict[str, str]:
    go_count = sum(1 for row in rows if row.get("go_no_go_state") == "go")
    no_go_count = len(rows) - go_count
    receipt_statuses = {row.get("current_status", "") for row in rows if row.get("checkpoint_name", "").endswith("_receipt")}
    if no_go_count == 0 and "wave24_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave24_extension_complete"
        recommended_next_action = (
            "Wave24 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave23_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave23_extension_complete"
        recommended_next_action = (
            "Wave23 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave22_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave22_extension_complete"
        recommended_next_action = (
            "Wave22 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave21_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave21_extension_complete"
        recommended_next_action = (
            "Wave21 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave20_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave20_extension_complete"
        recommended_next_action = (
            "Wave20 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave19_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave19_extension_complete"
        recommended_next_action = (
            "Wave19 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave18_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave18_extension_complete"
        recommended_next_action = (
            "Wave18 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave17_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave17_extension_complete"
        recommended_next_action = (
            "Wave17 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave16_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave16_extension_complete"
        recommended_next_action = (
            "Wave16 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave15_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave15_extension_complete"
        recommended_next_action = (
            "Wave15 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave14_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave14_extension_complete"
        recommended_next_action = (
            "Wave14 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave13_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave13_extension_complete"
        recommended_next_action = (
            "Wave13 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave12_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave12_extension_complete"
        recommended_next_action = (
            "Wave12 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave11_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave11_extension_complete"
        recommended_next_action = (
            "Wave11 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave10_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave10_extension_complete"
        recommended_next_action = (
            "Wave10 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave9_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave9_extension_complete"
        recommended_next_action = (
            "Wave9 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave8_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave8_extension_complete"
        recommended_next_action = (
            "Wave8 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave7_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave7_extension_complete"
        recommended_next_action = (
            "Wave7 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave6_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave6_extension_complete"
        recommended_next_action = (
            "Wave6 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0 and "wave5_presentation_extension_complete" in receipt_statuses:
        overall_state = "presentation_wave5_extension_complete"
        recommended_next_action = (
            "Wave5 presentation extension complete; README/UI refresh remains qualitative/demo only."
        )
        primary_boundary = "none_documented"
    elif no_go_count == 0:
        overall_state = "presentation_polish_complete"
        recommended_next_action = (
            "Presentation writeback complete; any README or UI refresh remains qualitative/demo and must not claim live delivery."
        )
        primary_boundary = "none_documented"
    elif go_count >= 4:
        overall_state = "presentation_writeback_ready"
        recommended_next_action = (
            "Proceed only with a narrow presentation writeback or delivery mockup; "
            "do not claim a live demo, recording, or public presentation without filled evidence receipts."
        )
        primary_boundary = "live_demo_claims_still_blocked"
    else:
        overall_state = "presentation_not_ready"
        recommended_next_action = "Complete storyboard and walkthrough review queues before any presentation writeback."
        primary_boundary = "live_demo_claims_still_blocked"
    return {
        "scope": "demo_go_no_go_board",
        "checkpoint_count": str(len(rows)),
        "go_count": str(go_count),
        "no_go_count": str(no_go_count),
        "overall_state": overall_state,
        "primary_boundary": primary_boundary,
        "recommended_next_action": recommended_next_action,
        "observation": (
            "qualitative/demo coordination board only; it separates presentation readiness "
            "from blocked live-delivery claims."
        ),
    }


def build_board_lines(rows: list[dict[str, str]]) -> list[str]:
    go_count = sum(1 for row in rows if row.get("go_no_go_state") == "go")
    lines = [
        "# Demo Go-No-Go Board",
        "",
        "This generated board compresses the current demo-excellence chain into a go/no-go view. "
        "It remains qualitative/demo and does not claim live demo or recording delivery.",
        "",
        f"Summary: `{go_count}/{len(rows)}` checkpoints are ready for a narrow presentation writeback path, while live-delivery claims remain blocked.",
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
        "# Demo Go-No-Go Summary",
        "",
        "This generated summary condenses the demo-excellence decision board into one action line. "
        "It remains qualitative/demo and does not claim live delivery.",
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

    board_csv = tables_dir / "demo_go_no_go_board.csv"
    board_json = tables_dir / "demo_go_no_go_board.json"
    summary_csv = tables_dir / "demo_go_no_go_summary.csv"
    summary_json = tables_dir / "demo_go_no_go_summary.json"
    board_md = figures_dir / "demo_go_no_go_board.md"
    summary_md = figures_dir / "demo_go_no_go_summary.md"

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
    print(f"Wrote demo go-no-go board CSV: {outputs[0].relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo go-no-go board JSON: {outputs[1].relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo go-no-go summary CSV: {outputs[2].relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo go-no-go summary JSON: {outputs[3].relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo go-no-go board note: {outputs[4].relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo go-no-go summary note: {outputs[5].relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
