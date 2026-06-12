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
    "diagnostic_case_scope",
    "candidate_case_scope",
    "execution_receipt_status",
    "blocker",
    "fill_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "coordination_scope",
    "wave18_closure_status",
    "heavyoverlap_prior_coordination_status",
    "midoverlap_refresh_status",
    "separation_benefit_signal",
    "expected_inputs",
    "writeback_note",
]


def load_json_dict(path_rel: str) -> dict[str, Any]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def assert_writeback_preconditions(
    wave18_receipt: dict[str, Any],
    demo_wave18_fill: dict[str, Any],
    heavyoverlap_receipt: dict[str, Any],
    midoverlap_refresh_receipt: dict[str, Any],
) -> None:
    if str(wave18_receipt.get("execution_status", "")) != "wave18_exploration_baseline_closure_complete":
        raise RuntimeError("Wave18 closure must be complete before HeavyOverlap diagnostic refresh coordination")
    if str(demo_wave18_fill.get("fill_status", "")) != "writeback_filled":
        raise RuntimeError("Demo Wave18 presentation writeback must be filled before HeavyOverlap coordination")
    if str(demo_wave18_fill.get("storyboard_receipt_status", "")) != "wave18_presentation_extension_complete":
        raise RuntimeError(
            "Demo Wave18 storyboard receipt must be wave18_presentation_extension_complete before HeavyOverlap coordination"
        )
    if str(heavyoverlap_receipt.get("execution_status", "")) != "speaker_profile_heavyoverlap_diagnostic_coordination_complete":
        raise RuntimeError(
            "Speaker profile HeavyOverlap diagnostic coordination must be complete before Wave18 refresh"
        )
    if str(midoverlap_refresh_receipt.get("execution_status", "")) != "wave17_speaker_profile_midoverlap_diagnostic_coordination_complete":
        raise RuntimeError(
            "Wave17 MidOverlap diagnostic refresh must be complete before HeavyOverlap refresh coordination"
        )
    if not (PROJECT_ROOT / "results/figures/separation_phase_diagram.md").exists():
        raise RuntimeError("Missing prerequisite artifact: results/figures/separation_phase_diagram.md")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "heavyoverlap_diagnostic_scope",
            "headline": "HeavyOverlap separation-benefit diagnostic scope refresh after Wave18 closure",
            "artifact_anchor": "results/figures/separation_phase_diagram.md",
            "coordination_note": "Separation helps ASR on this gold anchor; diagnostic-only — no attribution claim.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "heavyoverlap_prior",
            "headline": "Wave12 HeavyOverlap diagnostic coordination remains the prerequisite chain",
            "artifact_anchor": "results/figures/speaker_profile_heavyoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Wave18 refresh does not replace original HeavyOverlap boundary documentation.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "midoverlap_refresh",
            "headline": "Wave17 MidOverlap diagnostic refresh precedes HeavyOverlap refresh",
            "artifact_anchor": "results/figures/wave17_speaker_profile_midoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Overlap diagnostic chain progresses through coordinated refresh waves.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave18_boundary",
            "headline": "Wave18 closure defers overlap embedding execution to diagnostic boundaries only",
            "artifact_anchor": "results/figures/wave18_exploration_baseline_closure_card.md",
            "coordination_note": "Gold baseline CER tables unchanged; attribution still blocked.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "attribution_boundary",
            "headline": "HeavyOverlap refresh does not upgrade diagnostic scope to attribution claims",
            "artifact_anchor": "results/figures/speaker_profile_go_no_go_summary.md",
            "coordination_note": "Controlled benchmark timing required before separation-benefit attribution.",
            "result_label": "experimental/frontier",
        },
    ]


def build_fill_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_card",
        "coordination_section_count": str(len(rows)),
        "diagnostic_case_scope": "HeavyOverlap",
        "candidate_case_scope": "OppositeOverlap",
        "execution_receipt_status": "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_complete",
        "blocker": "attribution_claims_still_blocked",
        "fill_note": (
            "Documented HeavyOverlap diagnostic refresh after Wave18 closure; "
            "no overlap-case embedding execution claimed."
        ),
    }


def build_receipt_row(
    wave18_receipt: dict[str, Any],
    heavyoverlap_receipt: dict[str, Any],
    midoverlap_refresh_receipt: dict[str, Any],
) -> dict[str, str]:
    return {
        "execution_status": "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_complete",
        "coordination_scope": "wave18_speaker_profile_heavyoverlap_diagnostic",
        "wave18_closure_status": str(wave18_receipt.get("execution_status", "")),
        "heavyoverlap_prior_coordination_status": str(heavyoverlap_receipt.get("execution_status", "")),
        "midoverlap_refresh_status": str(midoverlap_refresh_receipt.get("execution_status", "")),
        "separation_benefit_signal": "separation_helps_on_heavyoverlap",
        "expected_inputs": (
            "Wave18 closure, demo wave18 writeback, Wave12 HeavyOverlap diagnostic, and Wave17 MidOverlap refresh."
        ),
        "writeback_note": (
            "experimental/frontier coordination only; does not claim overlap-case embedding execution."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Wave18 Speaker Profile HeavyOverlap Diagnostic Coordination Card (experimental/frontier)",
        "",
        "HeavyOverlap diagnostic refresh — not an embedding execution or attribution claim.",
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
        "# Wave18 Speaker Profile HeavyOverlap Diagnostic Coordination Writeback",
        "",
        "| fill_status | diagnostic_case_scope | execution_receipt_status | blocker |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['fill_status']} | {row['diagnostic_case_scope']} | "
            f"{row['execution_receipt_status']} | {row['blocker']} |"
        ),
    ]


def build_receipt_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Wave18 Speaker Profile HeavyOverlap Diagnostic Coordination Receipt",
        "",
        "| execution_status | heavyoverlap_prior_coordination_status | separation_benefit_signal |",
        "| --- | --- | --- |",
        (
            f"| {row['execution_status']} | {row['heavyoverlap_prior_coordination_status']} | "
            f"{row['separation_benefit_signal']} |"
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

    card_csv = tables_dir / "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_card.csv"
    card_json = tables_dir / "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_card.json"
    card_md = figures_dir / "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_card.md"
    fill_csv = tables_dir / "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.csv"
    fill_json = tables_dir / "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.json"
    fill_md = figures_dir / "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.md"
    receipt_json = tables_dir / "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_receipt.json"
    receipt_md = figures_dir / "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_receipt.md"

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
    demo_wave18_fill = load_json_dict("results/tables/demo_wave18_presentation_writeback.json")
    heavyoverlap_receipt = load_json_dict(
        "results/tables/speaker_profile_heavyoverlap_diagnostic_coordination_receipt.json"
    )
    midoverlap_refresh_receipt = load_json_dict(
        "results/tables/wave17_speaker_profile_midoverlap_diagnostic_coordination_receipt.json"
    )
    assert_writeback_preconditions(
        wave18_receipt, demo_wave18_fill, heavyoverlap_receipt, midoverlap_refresh_receipt
    )

    receipt_path = PROJECT_ROOT / "results/tables/wave18_speaker_profile_heavyoverlap_diagnostic_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict(
            "results/tables/wave18_speaker_profile_heavyoverlap_diagnostic_coordination_receipt.json"
        )
        if str(existing.get("execution_status", "")) == "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_complete",
                "blocker": "attribution_claims_still_blocked",
            }

    card_rows = build_coordination_rows()
    fill_row = build_fill_row(card_rows)
    receipt_row = build_receipt_row(wave18_receipt, heavyoverlap_receipt, midoverlap_refresh_receipt)
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "diagnostic_case_scope": fill_row["diagnostic_case_scope"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write Wave18 speaker profile HeavyOverlap diagnostic refresh after Wave18 closure."
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
