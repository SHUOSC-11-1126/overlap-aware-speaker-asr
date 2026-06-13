from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .io_helpers import build_card_lines as _build_card_lines, build_fill_lines as _build_fill_lines, load_json_dict


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
    "wave12_closure_status",
    "midoverlap_coordination_status",
    "separation_benefit_signal",
    "expected_inputs",
    "writeback_note",
]


def assert_writeback_preconditions(
    wave12_receipt: dict[str, Any],
    demo_wave12_fill: dict[str, Any],
    midoverlap_receipt: dict[str, Any],
) -> None:
    if str(wave12_receipt.get("execution_status", "")) != "wave12_exploration_baseline_closure_complete":
        raise RuntimeError("Wave12 closure must be complete before HeavyOverlap diagnostic coordination")
    if str(demo_wave12_fill.get("fill_status", "")) != "writeback_filled":
        raise RuntimeError("Demo Wave12 presentation writeback must be filled before HeavyOverlap coordination")
    if str(demo_wave12_fill.get("storyboard_receipt_status", "")) != "wave12_presentation_extension_complete":
        raise RuntimeError(
            "Demo Wave12 storyboard receipt must be wave12_presentation_extension_complete before HeavyOverlap coordination"
        )
    if str(midoverlap_receipt.get("execution_status", "")) != "speaker_profile_midoverlap_diagnostic_coordination_complete":
        raise RuntimeError(
            "Speaker profile MidOverlap diagnostic coordination must be complete before HeavyOverlap coordination"
        )
    if not (PROJECT_ROOT / "results/figures/separation_phase_diagram.md").exists():
        raise RuntimeError("Missing prerequisite artifact: results/figures/separation_phase_diagram.md")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "heavyoverlap_diagnostic_scope",
            "headline": "HeavyOverlap is the high-overlap separation-benefit diagnostic scope",
            "artifact_anchor": "results/figures/separation_phase_diagram.md",
            "coordination_note": "Separation helps ASR on this anchor; diagnostic-only — no attribution claim.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "midoverlap_prior",
            "headline": "MidOverlap diagnostic scope already coordinated",
            "artifact_anchor": "results/figures/speaker_profile_midoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Overlap diagnostic chain progresses through separation-harm then separation-benefit cases.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "opposite_overlap_deferred",
            "headline": "OppositeOverlap remains the final deferred diagnostic candidate",
            "artifact_anchor": "results/tables/speaker_profile_case_scope_coordination_card.json",
            "coordination_note": "Complete HeavyOverlap coordination before advancing OppositeOverlap scope.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave12_boundary",
            "headline": "Wave12 closure defers HeavyOverlap embedding execution to this diagnostic boundary",
            "artifact_anchor": "results/figures/wave12_exploration_baseline_closure_card.md",
            "coordination_note": "Gold baseline CER tables unchanged; attribution still blocked.",
            "result_label": "experimental/frontier",
        },
    ]


def build_fill_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "speaker_profile_heavyoverlap_diagnostic_coordination_card",
        "coordination_section_count": str(len(rows)),
        "diagnostic_case_scope": "HeavyOverlap",
        "candidate_case_scope": "OppositeOverlap",
        "execution_receipt_status": "speaker_profile_heavyoverlap_diagnostic_coordination_complete",
        "blocker": "attribution_claims_still_blocked",
        "fill_note": (
            "Documented HeavyOverlap as separation-benefit diagnostic scope after MidOverlap coordination; "
            "no overlap-case embedding execution claimed."
        ),
    }


def build_receipt_row(
    wave12_receipt: dict[str, Any],
    midoverlap_receipt: dict[str, Any],
) -> dict[str, str]:
    return {
        "execution_status": "speaker_profile_heavyoverlap_diagnostic_coordination_complete",
        "coordination_scope": "wave12_speaker_profile_heavyoverlap_diagnostic",
        "wave12_closure_status": str(wave12_receipt.get("execution_status", "")),
        "midoverlap_coordination_status": str(midoverlap_receipt.get("execution_status", "")),
        "separation_benefit_signal": "separation_helps_on_heavyoverlap",
        "expected_inputs": "Wave12 closure, demo wave12 writeback, MidOverlap diagnostic coordination, separation phase diagram.",
        "writeback_note": (
            "experimental/frontier diagnostic coordination only; does not record HeavyOverlap embedding execution."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    return _build_card_lines(rows, "HeavyOverlap")


def build_fill_lines(row: dict[str, str]) -> list[str]:
    return _build_fill_lines(row, "HeavyOverlap")


def build_receipt_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Speaker Profile HeavyOverlap Diagnostic Coordination Receipt",
        "",
        "| execution_status | separation_benefit_signal | midoverlap_coordination_status | blocker |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['execution_status']} | {row['separation_benefit_signal']} | "
            f"{row['midoverlap_coordination_status']} | attribution_claims_still_blocked |"
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

    card_csv = tables_dir / "speaker_profile_heavyoverlap_diagnostic_coordination_card.csv"
    card_json = tables_dir / "speaker_profile_heavyoverlap_diagnostic_coordination_card.json"
    card_md = figures_dir / "speaker_profile_heavyoverlap_diagnostic_coordination_card.md"
    fill_csv = tables_dir / "speaker_profile_heavyoverlap_diagnostic_coordination_writeback.csv"
    fill_json = tables_dir / "speaker_profile_heavyoverlap_diagnostic_coordination_writeback.json"
    fill_md = figures_dir / "speaker_profile_heavyoverlap_diagnostic_coordination_writeback.md"
    receipt_json = tables_dir / "speaker_profile_heavyoverlap_diagnostic_coordination_receipt.json"
    receipt_md = figures_dir / "speaker_profile_heavyoverlap_diagnostic_coordination_receipt.md"

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
    wave12_receipt = load_json_dict("results/tables/wave12_exploration_baseline_closure_receipt.json")
    demo_wave12_fill = load_json_dict("results/tables/demo_wave12_presentation_writeback.json")
    midoverlap_receipt = load_json_dict(
        "results/tables/speaker_profile_midoverlap_diagnostic_coordination_receipt.json"
    )
    assert_writeback_preconditions(wave12_receipt, demo_wave12_fill, midoverlap_receipt)

    receipt_path = PROJECT_ROOT / "results/tables/speaker_profile_heavyoverlap_diagnostic_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict("results/tables/speaker_profile_heavyoverlap_diagnostic_coordination_receipt.json")
        if str(existing.get("execution_status", "")) == "speaker_profile_heavyoverlap_diagnostic_coordination_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "speaker_profile_heavyoverlap_diagnostic_coordination_complete",
                "blocker": "attribution_claims_still_blocked",
            }

    card_rows = build_coordination_rows()
    fill_row = build_fill_row(card_rows)
    receipt_row = build_receipt_row(wave12_receipt, midoverlap_receipt)
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "diagnostic_case_scope": fill_row["diagnostic_case_scope"],
        "candidate_case_scope": fill_row["candidate_case_scope"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write speaker profile HeavyOverlap diagnostic coordination after Wave12 closure."
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
