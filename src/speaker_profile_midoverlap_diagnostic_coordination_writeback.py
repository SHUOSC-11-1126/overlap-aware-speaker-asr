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
    "wave9_closure_status",
    "lightoverlap_coordination_status",
    "separation_harm_signal",
    "expected_inputs",
    "writeback_note",
]


def assert_writeback_preconditions(
    wave9_receipt: dict[str, Any],
    lightoverlap_receipt: dict[str, Any],
) -> None:
    if str(wave9_receipt.get("execution_status", "")) != "wave9_exploration_baseline_closure_complete":
        raise RuntimeError("Wave9 closure must be complete before MidOverlap diagnostic coordination")
    if str(lightoverlap_receipt.get("execution_status", "")) != "speaker_profile_lightoverlap_diagnostic_coordination_complete":
        raise RuntimeError(
            "Speaker profile LightOverlap diagnostic coordination must be complete before MidOverlap coordination"
        )
    if not (PROJECT_ROOT / "results/figures/separation_phase_diagram.md").exists():
        raise RuntimeError("Missing prerequisite artifact: results/figures/separation_phase_diagram.md")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "midoverlap_diagnostic_scope",
            "headline": "MidOverlap is the final gold-case diagnostic embedding scope",
            "artifact_anchor": "results/figures/separation_phase_diagram.md",
            "coordination_note": "Separation harms ASR on this anchor; diagnostic-only — no attribution claim.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "lightoverlap_prior",
            "headline": "LightOverlap diagnostic scope already coordinated",
            "artifact_anchor": "results/figures/speaker_profile_lightoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Overlap diagnostic chain progresses NoOverlap → LightOverlap → MidOverlap.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "gold_case_coverage",
            "headline": "All five gold benchmark cases now have diagnostic scope boundaries",
            "artifact_anchor": "results/tables/speaker_profile_case_scope_coordination_card.json",
            "coordination_note": "Coordination only; no multi-case embedding execution claimed.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave9_boundary",
            "headline": "Wave9 closure defers MidOverlap embedding execution to this diagnostic boundary",
            "artifact_anchor": "results/figures/wave9_exploration_baseline_closure_card.md",
            "coordination_note": "Gold baseline CER tables unchanged; attribution still blocked.",
            "result_label": "experimental/frontier",
        },
    ]


def build_fill_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "speaker_profile_midoverlap_diagnostic_coordination_card",
        "coordination_section_count": str(len(rows)),
        "diagnostic_case_scope": "MidOverlap",
        "candidate_case_scope": "none_remaining",
        "execution_receipt_status": "speaker_profile_midoverlap_diagnostic_coordination_complete",
        "blocker": "attribution_claims_still_blocked",
        "fill_note": (
            "Documented MidOverlap as final diagnostic-only embedding scope after LightOverlap coordination; "
            "no overlap-case embedding execution claimed."
        ),
    }


def build_receipt_row(
    wave9_receipt: dict[str, Any],
    lightoverlap_receipt: dict[str, Any],
) -> dict[str, str]:
    return {
        "execution_status": "speaker_profile_midoverlap_diagnostic_coordination_complete",
        "coordination_scope": "wave9_speaker_profile_midoverlap_diagnostic",
        "wave9_closure_status": str(wave9_receipt.get("execution_status", "")),
        "lightoverlap_coordination_status": str(lightoverlap_receipt.get("execution_status", "")),
        "separation_harm_signal": "separation_hurts_on_midoverlap",
        "expected_inputs": "Wave9 closure, LightOverlap diagnostic coordination, separation phase diagram.",
        "writeback_note": (
            "experimental/frontier diagnostic coordination only; does not record MidOverlap embedding execution."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    return _build_card_lines(rows, "MidOverlap")


def build_fill_lines(row: dict[str, str]) -> list[str]:
    return _build_fill_lines(row, "MidOverlap")


def build_receipt_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Speaker Profile MidOverlap Diagnostic Coordination Receipt",
        "",
        "| execution_status | separation_harm_signal | lightoverlap_coordination_status | blocker |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['execution_status']} | {row['separation_harm_signal']} | "
            f"{row['lightoverlap_coordination_status']} | attribution_claims_still_blocked |"
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

    card_csv = tables_dir / "speaker_profile_midoverlap_diagnostic_coordination_card.csv"
    card_json = tables_dir / "speaker_profile_midoverlap_diagnostic_coordination_card.json"
    card_md = figures_dir / "speaker_profile_midoverlap_diagnostic_coordination_card.md"
    fill_csv = tables_dir / "speaker_profile_midoverlap_diagnostic_coordination_writeback.csv"
    fill_json = tables_dir / "speaker_profile_midoverlap_diagnostic_coordination_writeback.json"
    fill_md = figures_dir / "speaker_profile_midoverlap_diagnostic_coordination_writeback.md"
    receipt_json = tables_dir / "speaker_profile_midoverlap_diagnostic_coordination_receipt.json"
    receipt_md = figures_dir / "speaker_profile_midoverlap_diagnostic_coordination_receipt.md"

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
    wave9_receipt = load_json_dict("results/tables/wave9_exploration_baseline_closure_receipt.json")
    lightoverlap_receipt = load_json_dict(
        "results/tables/speaker_profile_lightoverlap_diagnostic_coordination_receipt.json"
    )
    assert_writeback_preconditions(wave9_receipt, lightoverlap_receipt)

    receipt_path = PROJECT_ROOT / "results/tables/speaker_profile_midoverlap_diagnostic_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict("results/tables/speaker_profile_midoverlap_diagnostic_coordination_receipt.json")
        if str(existing.get("execution_status", "")) == "speaker_profile_midoverlap_diagnostic_coordination_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "speaker_profile_midoverlap_diagnostic_coordination_complete",
                "blocker": "attribution_claims_still_blocked",
            }

    card_rows = build_coordination_rows()
    fill_row = build_fill_row(card_rows)
    receipt_row = build_receipt_row(wave9_receipt, lightoverlap_receipt)
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
        description="Write speaker profile MidOverlap diagnostic coordination after Wave9 closure."
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
