from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


CARD_COLUMNS = [
    "section_id",
    "headline",
    "artifact_anchor",
    "coordination_note",
    "result_label",
]

FILL_COLUMNS = [
    "fill_status",
    "writeback_scope",
    "coordination_section_count",
    "narrow_dry_run_case_count",
    "execution_receipt_status",
    "blocker",
    "fill_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "coordination_scope",
    "wave18_closure_status",
    "heavyoverlap_coordination_status",
    "llm_critic_board_state",
    "prior_llm_coordination_status",
    "expected_inputs",
    "writeback_note",
]


def load_json_dict(path_rel: str) -> dict[str, Any]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_json_rows(path_rel: str) -> list[dict[str, Any]]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def count_review_complete_cases() -> str:
    rows = load_json_rows("results/tables/llm_critic_review_pass_status.json")
    count = sum(1 for row in rows if str(row.get("pass_status", "")) == "review_complete")
    return str(count)


def assert_writeback_preconditions(
    wave18_receipt: dict[str, Any],
    heavyoverlap_receipt: dict[str, Any],
    demo_wave18_fill: dict[str, Any],
    llm_summary: dict[str, Any],
    prior_llm_receipt: dict[str, Any],
) -> None:
    if str(wave18_receipt.get("execution_status", "")) != "wave18_exploration_baseline_closure_complete":
        raise RuntimeError("Wave18 closure must be complete before LLM critic narrow dry-run coordination")
    if str(heavyoverlap_receipt.get("execution_status", "")) != "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_complete":
        raise RuntimeError(
            "Wave18 HeavyOverlap diagnostic coordination must be complete before LLM critic coordination"
        )
    if str(demo_wave18_fill.get("fill_status", "")) != "writeback_filled":
        raise RuntimeError("Demo Wave18 presentation writeback must be filled before LLM critic coordination")
    if str(demo_wave18_fill.get("storyboard_receipt_status", "")) != "wave18_presentation_extension_complete":
        raise RuntimeError(
            "Demo Wave18 storyboard receipt must be wave18_presentation_extension_complete before LLM critic coordination"
        )
    if str(llm_summary.get("overall_state", "")) != "qualitative_writeback_ready":
        raise RuntimeError(
            f"LLM critic board must be qualitative_writeback_ready; got {llm_summary.get('overall_state', 'missing')!r}"
        )
    if str(prior_llm_receipt.get("execution_status", "")) != "wave15_llm_critic_narrow_dry_run_coordination_complete":
        raise RuntimeError(
            "Wave15 LLM critic narrow dry-run coordination must be complete before Wave18 refresh"
        )
    review_count = int(count_review_complete_cases())
    if review_count < 5:
        raise RuntimeError(f"LLM critic narrow dry-run must cover 5/5 gold cases; got {review_count}")
    if not (PROJECT_ROOT / "results/tables/llm_critic_qualitative_brief_light_mid.json").exists():
        raise RuntimeError("Missing prerequisite artifact: results/tables/llm_critic_qualitative_brief_light_mid.json")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "review_pass_queue",
            "headline": "Qualitative review pass queue dry-run remains complete on 5/5 gold cases",
            "artifact_anchor": "results/tables/llm_critic_review_pass_status.json",
            "coordination_note": "qualitative/demo dry-run only; not verified transcript repair.",
            "result_label": "qualitative/demo",
        },
        {
            "section_id": "qualitative_brief_boundary",
            "headline": "Light/Mid overlap qualitative brief documents critic hypotheses only",
            "artifact_anchor": "results/figures/llm_critic_qualitative_brief_light_mid.md",
            "coordination_note": "Separation-harm hypotheses; does not claim verified correction.",
            "result_label": "qualitative/demo",
        },
        {
            "section_id": "heavyoverlap_prior",
            "headline": "Wave18 HeavyOverlap diagnostic coordination precedes critic narrow dry-run refresh",
            "artifact_anchor": "results/figures/wave18_speaker_profile_heavyoverlap_diagnostic_coordination_card.md",
            "coordination_note": "experimental/frontier diagnostic chain provides slice context only.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave18_boundary",
            "headline": "Wave18 closure keeps LLM critic dry-run separate from gold baseline CER",
            "artifact_anchor": "results/figures/wave18_exploration_baseline_closure_card.md",
            "coordination_note": "Coordination writeback only; stable gold CER tables unchanged.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "verified_repair_boundary",
            "headline": "Narrow dry-run refresh does not upgrade qualitative notes to verified repair",
            "artifact_anchor": "results/figures/llm_critic_go_no_go_summary.md",
            "coordination_note": "README mentions must keep qualitative/demo labeling.",
            "result_label": "qualitative/demo",
        },
    ]


def build_fill_row(rows: list[dict[str, str]], narrow_dry_run_case_count: str) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "wave18_llm_critic_narrow_dry_run_coordination_card",
        "coordination_section_count": str(len(rows)),
        "narrow_dry_run_case_count": narrow_dry_run_case_count,
        "execution_receipt_status": "wave18_llm_critic_narrow_dry_run_coordination_complete",
        "blocker": "verified_repair_claims_still_blocked",
        "fill_note": (
            "Documented LLM critic narrow dry-run refresh boundary after Wave18 HeavyOverlap chain; "
            "verified repair claims remain blocked."
        ),
    }


def build_receipt_row(
    wave18_receipt: dict[str, Any],
    heavyoverlap_receipt: dict[str, Any],
    llm_summary: dict[str, Any],
    prior_llm_receipt: dict[str, Any],
) -> dict[str, str]:
    return {
        "execution_status": "wave18_llm_critic_narrow_dry_run_coordination_complete",
        "coordination_scope": "wave18_llm_critic_narrow_dry_run",
        "wave18_closure_status": str(wave18_receipt.get("execution_status", "")),
        "heavyoverlap_coordination_status": str(heavyoverlap_receipt.get("execution_status", "")),
        "llm_critic_board_state": str(llm_summary.get("overall_state", "")),
        "prior_llm_coordination_status": str(prior_llm_receipt.get("execution_status", "")),
        "expected_inputs": (
            "Wave18 closure, HeavyOverlap diagnostic, demo wave18, LLM critic review pass status."
        ),
        "writeback_note": (
            "qualitative/demo coordination only; does not claim verified transcript correction or live LLM execution."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Wave18 LLM Critic Narrow Dry-Run Coordination Card (qualitative/demo)",
        "",
        "Narrow dry-run refresh boundary coordination — not a verified repair completion claim.",
        "",
        "| section_id | headline | artifact_anchor | result_label |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['section_id']} | {row['headline']} | {row['artifact_anchor']} | {row['result_label']} |"
        )
    lines.append("")
    for row in rows:
        lines.append(f"- **{row['section_id']}**: {row['coordination_note']}")
    return lines


def build_fill_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Wave18 LLM Critic Narrow Dry-Run Coordination Writeback",
        "",
        "| fill_status | narrow_dry_run_case_count | execution_receipt_status | blocker |",
        "| --- | ---: | --- | --- |",
        (
            f"| {row['fill_status']} | {row['narrow_dry_run_case_count']} | "
            f"{row['execution_receipt_status']} | {row['blocker']} |"
        ),
    ]


def build_receipt_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Wave18 LLM Critic Narrow Dry-Run Coordination Receipt",
        "",
        "| execution_status | heavyoverlap_coordination_status | llm_critic_board_state | blocker |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['execution_status']} | {row['heavyoverlap_coordination_status']} | "
            f"{row['llm_critic_board_state']} | verified_repair_claims_still_blocked |"
        ),
    ]


def write_outputs(
    card_rows: list[dict[str, str]],
    fill_row: dict[str, str],
    receipt_row: dict[str, str],
) -> Path:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    card_csv = tables_dir / "wave18_llm_critic_narrow_dry_run_coordination_card.csv"
    card_json = tables_dir / "wave18_llm_critic_narrow_dry_run_coordination_card.json"
    card_md = figures_dir / "wave18_llm_critic_narrow_dry_run_coordination_card.md"
    fill_csv = tables_dir / "wave18_llm_critic_narrow_dry_run_coordination_writeback.csv"
    fill_json = tables_dir / "wave18_llm_critic_narrow_dry_run_coordination_writeback.json"
    fill_md = figures_dir / "wave18_llm_critic_narrow_dry_run_coordination_writeback.md"
    receipt_json = tables_dir / "wave18_llm_critic_narrow_dry_run_coordination_receipt.json"
    receipt_md = figures_dir / "wave18_llm_critic_narrow_dry_run_coordination_receipt.md"

    with card_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CARD_COLUMNS)
        writer.writeheader()
        writer.writerows(card_rows)
    card_json.write_text(json.dumps(card_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    card_md.write_text("\n".join(build_card_lines(card_rows)) + "\n", encoding="utf-8")

    with fill_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FILL_COLUMNS)
        writer.writeheader()
        writer.writerow(fill_row)
    fill_json.write_text(json.dumps(fill_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fill_md.write_text("\n".join(build_fill_lines(fill_row)) + "\n", encoding="utf-8")
    receipt_json.write_text(json.dumps(receipt_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt_md.write_text("\n".join(build_receipt_lines(receipt_row)) + "\n", encoding="utf-8")
    return fill_json


def run_coordination_writeback(force: bool = False) -> dict[str, str]:
    wave18_receipt = load_json_dict("results/tables/wave18_exploration_baseline_closure_receipt.json")
    heavyoverlap_receipt = load_json_dict(
        "results/tables/wave18_speaker_profile_heavyoverlap_diagnostic_coordination_receipt.json"
    )
    demo_wave18_fill = load_json_dict("results/tables/demo_wave18_presentation_writeback.json")
    llm_summary = load_json_dict("results/tables/llm_critic_go_no_go_summary.json")
    prior_llm_receipt = load_json_dict(
        "results/tables/wave15_llm_critic_narrow_dry_run_coordination_receipt.json"
    )
    assert_writeback_preconditions(
        wave18_receipt, heavyoverlap_receipt, demo_wave18_fill, llm_summary, prior_llm_receipt
    )

    receipt_path = PROJECT_ROOT / "results/tables/wave18_llm_critic_narrow_dry_run_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict("results/tables/wave18_llm_critic_narrow_dry_run_coordination_receipt.json")
        if str(existing.get("execution_status", "")) == "wave18_llm_critic_narrow_dry_run_coordination_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "wave18_llm_critic_narrow_dry_run_coordination_complete",
                "blocker": "verified_repair_claims_still_blocked",
            }

    review_count = count_review_complete_cases()
    card_rows = build_coordination_rows()
    fill_row = build_fill_row(card_rows, review_count)
    receipt_row = build_receipt_row(wave18_receipt, heavyoverlap_receipt, llm_summary, prior_llm_receipt)
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "narrow_dry_run_case_count": fill_row["narrow_dry_run_case_count"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write Wave18 LLM critic narrow dry-run coordination after HeavyOverlap chain."
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an already-filled coordination receipt.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_coordination_writeback(force=args.force)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
