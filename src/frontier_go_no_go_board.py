from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BOARD_COLUMNS = [
    "frontier_name",
    "current_state",
    "primary_boundary",
    "go_no_go_state",
    "recommended_next_action",
    "evidence_artifact",
]

SUMMARY_COLUMNS = [
    "scope",
    "frontier_count",
    "go_count",
    "no_go_count",
    "highest_priority_ready_frontier",
    "highest_priority_blocked_frontier",
    "coordination_state",
    "recommended_operator_focus",
    "observation",
]

FRONTIER_ORDER = [
    "meeteval_compatibility",
    "external_validation",
    "speaker_profile",
    "llm_critic",
    "demo_excellence",
]


def load_json_payload(path_rel: str) -> dict | list:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, (dict, list)) else {}


def classify_go_no_go_state(current_state: str) -> str:
    lowered = current_state.strip().lower()
    ready_markers = {
        "receipt_ready_to_fill",
        "narrow_execution_ready",
        "qualitative_writeback_ready",
        "presentation_writeback_ready",
        "presentation_polish_complete",
        "character_level_receipt_fill_complete",
        "meeteval_cpwer_narrow_dry_run_coordination_complete",
        "meeteval_official_narrow_dry_run_coordination_complete",
        "wave20_meeteval_official_narrow_dry_run_coordination_complete",
        "wave26_meeteval_official_narrow_dry_run_coordination_complete",
        "wave30_meeteval_official_narrow_dry_run_coordination_complete",
        "wave34_meeteval_official_narrow_dry_run_coordination_complete",
        "wave38_meeteval_official_narrow_dry_run_coordination_complete",
        "presentation_wave5_extension_complete",
        "presentation_wave6_extension_complete",
        "presentation_wave7_extension_complete",
        "presentation_wave8_extension_complete",
        "presentation_wave9_extension_complete",
        "presentation_wave10_extension_complete",
        "wave6_coordination_closure_complete",
        "wave7_exploration_baseline_closure_complete",
        "wave8_exploration_baseline_closure_complete",
        "wave9_exploration_baseline_closure_complete",
        "wave10_exploration_baseline_closure_complete",
        "wave11_exploration_baseline_closure_complete",
        "wave12_exploration_baseline_closure_complete",
        "wave13_exploration_baseline_closure_complete",
        "wave14_exploration_baseline_closure_complete",
        "wave15_exploration_baseline_closure_complete",
        "wave16_exploration_baseline_closure_complete",
        "wave17_exploration_baseline_closure_complete",
        "wave18_exploration_baseline_closure_complete",
        "wave19_exploration_baseline_closure_complete",
        "wave20_exploration_baseline_closure_complete",
        "wave21_exploration_baseline_closure_complete",
        "wave22_exploration_baseline_closure_complete",
        "wave23_exploration_baseline_closure_complete",
        "wave24_exploration_baseline_closure_complete",
        "wave25_exploration_baseline_closure_complete",
        "wave26_exploration_baseline_closure_complete",
        "wave27_exploration_baseline_closure_complete",
        "wave28_exploration_baseline_closure_complete",
        "wave29_exploration_baseline_closure_complete",
        "wave30_exploration_baseline_closure_complete",
        "wave31_exploration_baseline_closure_complete",
        "wave32_exploration_baseline_closure_complete",
        "wave33_exploration_baseline_closure_complete",
        "wave34_exploration_baseline_closure_complete",
        "wave35_exploration_baseline_closure_complete",
        "wave36_exploration_baseline_closure_complete",
        "wave37_exploration_baseline_closure_complete",
        "wave38_exploration_baseline_closure_complete",
        "wave39_exploration_baseline_closure_complete",
        "wave40_exploration_baseline_closure_complete",
        "wave41_exploration_baseline_closure_complete",
        "wave19_speaker_profile_oppositeoverlap_diagnostic_coordination_complete",
        "wave24_speaker_profile_oppositeoverlap_diagnostic_coordination_complete",
        "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_complete",
        "wave23_speaker_profile_heavyoverlap_diagnostic_coordination_complete",
        "speaker_profile_case_scope_coordination_complete",
        "speaker_profile_lightoverlap_diagnostic_coordination_complete",
        "wave16_speaker_profile_lightoverlap_diagnostic_coordination_complete",
        "wave21_speaker_profile_lightoverlap_diagnostic_coordination_complete",
        "wave27_speaker_profile_lightoverlap_diagnostic_coordination_complete",
        "wave31_speaker_profile_lightoverlap_diagnostic_coordination_complete",
        "wave35_speaker_profile_lightoverlap_diagnostic_coordination_complete",
        "wave39_speaker_profile_lightoverlap_diagnostic_coordination_complete",
        "wave17_speaker_profile_midoverlap_diagnostic_coordination_complete",
        "wave22_speaker_profile_midoverlap_diagnostic_coordination_complete",
        "wave28_speaker_profile_midoverlap_diagnostic_coordination_complete",
        "wave32_speaker_profile_midoverlap_diagnostic_coordination_complete",
        "wave36_speaker_profile_midoverlap_diagnostic_coordination_complete",
        "wave40_speaker_profile_midoverlap_diagnostic_coordination_complete",
        "wave17_meeteval_cpwer_narrow_dry_run_coordination_complete",
        "speaker_profile_midoverlap_diagnostic_coordination_complete",
        "speaker_profile_heavyoverlap_diagnostic_coordination_complete",
        "speaker_profile_oppositeoverlap_diagnostic_coordination_complete",
        "cascade_benchmark_evidence_receipt_coordination_complete",
        "cascade_benchmark_phase1_gate_coordination_complete",
        "cascade_benchmark_phase2_gate_coordination_complete",
        "cascade_benchmark_phase3_gate_coordination_complete",
        "cascade_benchmark_phase4_gate_coordination_complete",
        "cascade_benchmark_phase5_gate_coordination_complete",
        "external_validation_narrow_slice_coordination_complete",
        "wave15_external_validation_narrow_slice_coordination_complete",
        "wave19_external_validation_narrow_slice_coordination_complete",
        "wave25_external_validation_narrow_slice_coordination_complete",
        "wave29_external_validation_narrow_slice_coordination_complete",
        "wave33_external_validation_narrow_slice_coordination_complete",
        "wave37_external_validation_narrow_slice_coordination_complete",
        "llm_critic_narrow_dry_run_coordination_complete",
        "wave15_llm_critic_narrow_dry_run_coordination_complete",
        "wave18_llm_critic_narrow_dry_run_coordination_complete",
        "ready_for_narrow_audio_eval",
    }
    if lowered in ready_markers:
        return "go"
    return "no_go"


def build_frontier_rows() -> list[dict[str, str]]:
    meeteval_receipt = load_json_payload("results/tables/meeteval_cpwer_execution_receipt_readiness.json")
    meeteval_token = load_json_payload("results/tables/meeteval_cpwer_tokenization_adaptation_completion_summary.json")
    external_summary = load_json_payload("results/tables/external_validation_go_no_go_summary.json")
    external_coord = load_json_payload("results/tables/external_validation_narrow_slice_coordination_receipt.json")
    external_coord_status = str((external_coord if isinstance(external_coord, dict) else {}).get("execution_status", ""))
    speaker_summary = load_json_payload("results/tables/speaker_profile_go_no_go_summary.json")
    llm_summary = load_json_payload("results/tables/llm_critic_go_no_go_summary.json")
    llm_coord = load_json_payload("results/tables/llm_critic_narrow_dry_run_coordination_receipt.json")
    llm_coord_status = str((llm_coord if isinstance(llm_coord, dict) else {}).get("execution_status", ""))
    demo_summary = load_json_payload("results/tables/demo_go_no_go_summary.json")

    meeteval_receipt_status = str((meeteval_receipt if isinstance(meeteval_receipt, dict) else {}).get("readiness_status", ""))
    meeteval_token_status = str((meeteval_token if isinstance(meeteval_token, dict) else {}).get("queue_status", ""))
    wave6_closure = load_json_payload("results/tables/wave6_frontier_coordination_closure_receipt.json")
    wave6_closure_status = str((wave6_closure if isinstance(wave6_closure, dict) else {}).get("execution_status", ""))
    narrow_coord = load_json_payload("results/tables/meeteval_cpwer_narrow_dry_run_coordination_receipt.json")
    narrow_coord_status = str((narrow_coord if isinstance(narrow_coord, dict) else {}).get("execution_status", ""))
    if narrow_coord_status == "meeteval_cpwer_narrow_dry_run_coordination_complete" and meeteval_token_status == "queue_complete":
        meeteval_state = "meeteval_cpwer_narrow_dry_run_coordination_complete"
    elif wave6_closure_status == "wave6_coordination_closure_complete" and meeteval_token_status == "queue_complete":
        meeteval_state = "wave6_coordination_closure_complete"
    elif meeteval_receipt_status == "character_level_receipt_fill_complete" and meeteval_token_status == "queue_complete":
        meeteval_state = "character_level_receipt_fill_complete"
    elif meeteval_receipt_status == "receipt_ready_to_fill" and meeteval_token_status == "queue_complete":
        meeteval_state = "receipt_ready_to_fill"
    else:
        meeteval_state = "meeteval_not_ready"

    rows = [
        {
            "frontier_name": "meeteval_compatibility",
            "current_state": meeteval_state,
            "primary_boundary": "official_benchmark_claims_still_blocked_until_receipt_fill",
            "go_no_go_state": classify_go_no_go_state(meeteval_state),
            "recommended_next_action": "If execution starts, use character-spaced cpWER and fill the official receipt with real evidence.",
            "evidence_artifact": "results/figures/meeteval_cpwer_tokenization_gain_scorecard_summary.md",
        },
        {
            "frontier_name": "external_validation",
            "current_state": (
                "external_validation_narrow_slice_coordination_complete"
                if external_coord_status == "external_validation_narrow_slice_coordination_complete"
                else str((external_summary if isinstance(external_summary, dict) else {}).get("overall_state", ""))
            ),
            "primary_boundary": (
                "gold_benchmark_claims_still_blocked"
                if external_coord_status == "external_validation_narrow_slice_coordination_complete"
                else str((external_summary if isinstance(external_summary, dict) else {}).get("primary_blocker", "license_confirmation_pending"))
            ),
            "go_no_go_state": classify_go_no_go_state(
                "external_validation_narrow_slice_coordination_complete"
                if external_coord_status == "external_validation_narrow_slice_coordination_complete"
                else str((external_summary if isinstance(external_summary, dict) else {}).get("overall_state", ""))
            ),
            "recommended_next_action": (
                "Narrow slice coordination complete; any README mention stays external/sanity-check only."
                if external_coord_status == "external_validation_narrow_slice_coordination_complete"
                else str((external_summary if isinstance(external_summary, dict) else {}).get("recommended_next_action", ""))
            ),
            "evidence_artifact": "results/figures/external_validation_go_no_go_summary.md",
        },
        {
            "frontier_name": "speaker_profile",
            "current_state": str((speaker_summary if isinstance(speaker_summary, dict) else {}).get("overall_state", "")),
            "primary_boundary": str((speaker_summary if isinstance(speaker_summary, dict) else {}).get("primary_boundary", "")),
            "go_no_go_state": classify_go_no_go_state(str((speaker_summary if isinstance(speaker_summary, dict) else {}).get("overall_state", ""))),
            "recommended_next_action": str((speaker_summary if isinstance(speaker_summary, dict) else {}).get("recommended_next_action", "")),
            "evidence_artifact": "results/figures/speaker_profile_go_no_go_summary.md",
        },
        {
            "frontier_name": "llm_critic",
            "current_state": (
                "llm_critic_narrow_dry_run_coordination_complete"
                if llm_coord_status == "llm_critic_narrow_dry_run_coordination_complete"
                else str((llm_summary if isinstance(llm_summary, dict) else {}).get("overall_state", ""))
            ),
            "primary_boundary": (
                "verified_repair_claims_still_blocked"
                if llm_coord_status == "llm_critic_narrow_dry_run_coordination_complete"
                else str((llm_summary if isinstance(llm_summary, dict) else {}).get("primary_boundary", ""))
            ),
            "go_no_go_state": classify_go_no_go_state(
                "llm_critic_narrow_dry_run_coordination_complete"
                if llm_coord_status == "llm_critic_narrow_dry_run_coordination_complete"
                else str((llm_summary if isinstance(llm_summary, dict) else {}).get("overall_state", ""))
            ),
            "recommended_next_action": (
                "Narrow dry-run coordination complete; any README mention stays qualitative/demo only."
                if llm_coord_status == "llm_critic_narrow_dry_run_coordination_complete"
                else str((llm_summary if isinstance(llm_summary, dict) else {}).get("recommended_next_action", ""))
            ),
            "evidence_artifact": "results/figures/llm_critic_go_no_go_summary.md",
        },
        {
            "frontier_name": "demo_excellence",
            "current_state": str((demo_summary if isinstance(demo_summary, dict) else {}).get("overall_state", "")),
            "primary_boundary": str((demo_summary if isinstance(demo_summary, dict) else {}).get("primary_boundary", "")),
            "go_no_go_state": classify_go_no_go_state(str((demo_summary if isinstance(demo_summary, dict) else {}).get("overall_state", ""))),
            "recommended_next_action": str((demo_summary if isinstance(demo_summary, dict) else {}).get("recommended_next_action", "")),
            "evidence_artifact": "results/figures/demo_go_no_go_summary.md",
        },
    ]
    return rows


def _priority_pick(rows: list[dict[str, str]], desired_state: str) -> str:
    rows_by_name = {row["frontier_name"]: row for row in rows}
    for frontier_name in FRONTIER_ORDER:
        row = rows_by_name.get(frontier_name)
        if row and row.get("go_no_go_state") == desired_state:
            return frontier_name
    return ""


def build_summary_row(rows: list[dict[str, str]]) -> dict[str, str]:
    go_count = sum(1 for row in rows if row.get("go_no_go_state") == "go")
    no_go_count = len(rows) - go_count
    highest_priority_ready = _priority_pick(rows, "go")
    highest_priority_blocked = _priority_pick(rows, "no_go")
    coordination_state = "mixed_ready_state" if go_count and no_go_count else ("all_ready" if go_count else "all_blocked")
    recommended_focus = highest_priority_ready or highest_priority_blocked
    return {
        "scope": "frontier_go_no_go_board",
        "frontier_count": str(len(rows)),
        "go_count": str(go_count),
        "no_go_count": str(no_go_count),
        "highest_priority_ready_frontier": highest_priority_ready,
        "highest_priority_blocked_frontier": highest_priority_blocked,
        "coordination_state": coordination_state,
        "recommended_operator_focus": recommended_focus,
        "observation": (
            "Top-level coordination board only; it summarizes narrow next-step readiness "
            "without claiming frontier completion."
        ),
    }


def build_board_lines(rows: list[dict[str, str]]) -> list[str]:
    go_count = sum(1 for row in rows if row.get("go_no_go_state") == "go")
    lines = [
        "# Frontier Go-No-Go Board",
        "",
        "This generated board compresses the five frontier tracks into one coordination view. "
        "It does not claim that any frontier has been fully completed merely because a narrow next step is ready.",
        "",
        f"Summary: `{go_count}/{len(rows)}` frontier tracks are ready for a narrow next action in the current queue state.",
        "",
        "| frontier_name | current_state | primary_boundary | go_no_go_state | recommended_next_action | evidence_artifact |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['frontier_name']} | {row['current_state']} | {row['primary_boundary']} | "
            f"{row['go_no_go_state']} | {row['recommended_next_action']} | {row['evidence_artifact']} |"
        )
    return lines


def build_summary_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Frontier Go-No-Go Summary",
        "",
        "This generated summary condenses the top-level frontier board into one operator-facing recommendation.",
        "",
        "| scope | frontier_count | go_count | no_go_count | highest_priority_ready_frontier | highest_priority_blocked_frontier | coordination_state | recommended_operator_focus | observation |",
        "| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- |",
        (
            f"| {row['scope']} | {row['frontier_count']} | {row['go_count']} | {row['no_go_count']} | "
            f"{row['highest_priority_ready_frontier']} | {row['highest_priority_blocked_frontier']} | "
            f"{row['coordination_state']} | {row['recommended_operator_focus']} | {row['observation']} |"
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

    board_csv = tables_dir / "frontier_go_no_go_board.csv"
    board_json = tables_dir / "frontier_go_no_go_board.json"
    summary_csv = tables_dir / "frontier_go_no_go_summary.csv"
    summary_json = tables_dir / "frontier_go_no_go_summary.json"
    board_md = figures_dir / "frontier_go_no_go_board.md"
    summary_md = figures_dir / "frontier_go_no_go_summary.md"

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
    rows = build_frontier_rows()
    summary_row = build_summary_row(rows)
    outputs = write_outputs(rows, summary_row)
    print(f"Wrote frontier go-no-go board CSV: {outputs[0].relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier go-no-go board JSON: {outputs[1].relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier go-no-go summary CSV: {outputs[2].relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier go-no-go summary JSON: {outputs[3].relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier go-no-go board note: {outputs[4].relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier go-no-go summary note: {outputs[5].relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
