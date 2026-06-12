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
    "wave36_closure_status",
    "midoverlap_prior_coordination_status",
    "wave32_refresh_status",
    "lightoverlap_refresh_status",
    "separation_harm_signal",
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
    wave36_receipt: dict[str, Any],
    demo_wave36_fill: dict[str, Any],
    midoverlap_receipt: dict[str, Any],
    wave32_refresh_receipt: dict[str, Any],
    lightoverlap_refresh_receipt: dict[str, Any],
) -> None:
    if str(wave36_receipt.get("execution_status", "")) != "wave36_exploration_baseline_closure_complete":
        raise RuntimeError("Wave36 closure must be complete before MidOverlap diagnostic refresh coordination")
    if str(demo_wave36_fill.get("fill_status", "")) != "writeback_filled":
        raise RuntimeError("Demo Wave36 presentation writeback must be filled before MidOverlap coordination")
    if str(demo_wave36_fill.get("storyboard_receipt_status", "")) != "wave36_presentation_extension_complete":
        raise RuntimeError(
            "Demo Wave36 storyboard receipt must be wave36_presentation_extension_complete before MidOverlap coordination"
        )
    if str(midoverlap_receipt.get("execution_status", "")) != "speaker_profile_midoverlap_diagnostic_coordination_complete":
        raise RuntimeError(
            "Speaker profile MidOverlap diagnostic coordination must be complete before Wave36 refresh"
        )
    if (
        str(wave32_refresh_receipt.get("execution_status", ""))
        != "wave32_speaker_profile_midoverlap_diagnostic_coordination_complete"
    ):
        raise RuntimeError(
            "Wave32 MidOverlap diagnostic refresh must be complete before Wave36 refresh coordination"
        )
    if (
        str(lightoverlap_refresh_receipt.get("execution_status", ""))
        != "wave35_speaker_profile_lightoverlap_diagnostic_coordination_complete"
    ):
        raise RuntimeError(
            "Wave35 LightOverlap diagnostic refresh must be complete before MidOverlap refresh coordination"
        )
    if not (PROJECT_ROOT / "results/figures/separation_phase_diagram.md").exists():
        raise RuntimeError("Missing prerequisite artifact: results/figures/separation_phase_diagram.md")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "midoverlap_diagnostic_scope",
            "headline": "MidOverlap separation-harm diagnostic scope refresh after Wave36 closure",
            "artifact_anchor": "results/figures/separation_phase_diagram.md",
            "coordination_note": "Separation harms ASR on this gold anchor; diagnostic-only — no attribution claim.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "midoverlap_prior",
            "headline": "Wave9 MidOverlap diagnostic coordination remains the prerequisite chain",
            "artifact_anchor": "results/figures/speaker_profile_midoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Wave36 refresh does not replace original MidOverlap boundary documentation.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave32_refresh",
            "headline": "Wave32 MidOverlap diagnostic refresh precedes Wave36 refresh",
            "artifact_anchor": "results/figures/wave32_speaker_profile_midoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Prior wave refresh provides chain for cyclic overlap diagnostic coordination.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "lightoverlap_refresh",
            "headline": "Wave35 LightOverlap diagnostic refresh precedes MidOverlap refresh",
            "artifact_anchor": "results/figures/wave35_speaker_profile_lightoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Overlap diagnostic chain progresses LightOverlap → MidOverlap through coordinated refreshes.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave36_boundary",
            "headline": "Wave36 closure defers overlap embedding execution to diagnostic boundaries only",
            "artifact_anchor": "results/figures/wave36_exploration_baseline_closure_card.md",
            "coordination_note": "Gold baseline CER tables unchanged; attribution still blocked.",
            "result_label": "experimental/frontier",
        },
    ]


def build_fill_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "wave36_speaker_profile_midoverlap_diagnostic_coordination_card",
        "coordination_section_count": str(len(rows)),
        "diagnostic_case_scope": "MidOverlap",
        "candidate_case_scope": "HeavyOverlap",
        "execution_receipt_status": "wave36_speaker_profile_midoverlap_diagnostic_coordination_complete",
        "blocker": "attribution_claims_still_blocked",
        "fill_note": (
            "Documented MidOverlap diagnostic refresh after Wave36 closure; "
            "no overlap-case embedding execution claimed."
        ),
    }


def build_receipt_row(
    wave36_receipt: dict[str, Any],
    midoverlap_receipt: dict[str, Any],
    wave32_refresh_receipt: dict[str, Any],
    lightoverlap_refresh_receipt: dict[str, Any],
) -> dict[str, str]:
    return {
        "execution_status": "wave36_speaker_profile_midoverlap_diagnostic_coordination_complete",
        "coordination_scope": "wave36_speaker_profile_midoverlap_diagnostic",
        "wave36_closure_status": str(wave36_receipt.get("execution_status", "")),
        "midoverlap_prior_coordination_status": str(midoverlap_receipt.get("execution_status", "")),
        "wave32_refresh_status": str(wave32_refresh_receipt.get("execution_status", "")),
        "lightoverlap_refresh_status": str(lightoverlap_refresh_receipt.get("execution_status", "")),
        "separation_harm_signal": "separation_hurts_on_midoverlap",
        "expected_inputs": (
            "Wave36 closure, demo wave36, Wave9 MidOverlap, Wave32 refresh, and Wave35 LightOverlap refresh."
        ),
        "writeback_note": (
            "experimental/frontier coordination only; does not claim overlap-case embedding execution."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Wave36 Speaker Profile MidOverlap Diagnostic Coordination Card (experimental/frontier)",
        "",
        "MidOverlap diagnostic refresh — not an embedding execution or attribution claim.",
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
        "# Wave36 Speaker Profile MidOverlap Diagnostic Coordination Writeback",
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
        "# Wave36 Speaker Profile MidOverlap Diagnostic Coordination Receipt",
        "",
        "| execution_status | wave32_refresh_status | lightoverlap_refresh_status |",
        "| --- | --- | --- |",
        (
            f"| {row['execution_status']} | {row['wave32_refresh_status']} | "
            f"{row['lightoverlap_refresh_status']} |"
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

    card_csv = tables_dir / "wave36_speaker_profile_midoverlap_diagnostic_coordination_card.csv"
    card_json = tables_dir / "wave36_speaker_profile_midoverlap_diagnostic_coordination_card.json"
    card_md = figures_dir / "wave36_speaker_profile_midoverlap_diagnostic_coordination_card.md"
    fill_csv = tables_dir / "wave36_speaker_profile_midoverlap_diagnostic_coordination_writeback.csv"
    fill_json = tables_dir / "wave36_speaker_profile_midoverlap_diagnostic_coordination_writeback.json"
    fill_md = figures_dir / "wave36_speaker_profile_midoverlap_diagnostic_coordination_writeback.md"
    receipt_json = tables_dir / "wave36_speaker_profile_midoverlap_diagnostic_coordination_receipt.json"
    receipt_md = figures_dir / "wave36_speaker_profile_midoverlap_diagnostic_coordination_receipt.md"

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
    wave36_receipt = load_json_dict("results/tables/wave36_exploration_baseline_closure_receipt.json")
    demo_wave36_fill = load_json_dict("results/tables/demo_wave36_presentation_writeback.json")
    midoverlap_receipt = load_json_dict(
        "results/tables/speaker_profile_midoverlap_diagnostic_coordination_receipt.json"
    )
    wave32_refresh_receipt = load_json_dict(
        "results/tables/wave32_speaker_profile_midoverlap_diagnostic_coordination_receipt.json"
    )
    lightoverlap_refresh_receipt = load_json_dict(
        "results/tables/wave35_speaker_profile_lightoverlap_diagnostic_coordination_receipt.json"
    )
    assert_writeback_preconditions(
        wave36_receipt,
        demo_wave36_fill,
        midoverlap_receipt,
        wave32_refresh_receipt,
        lightoverlap_refresh_receipt,
    )

    receipt_path = PROJECT_ROOT / "results/tables/wave36_speaker_profile_midoverlap_diagnostic_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict(
            "results/tables/wave36_speaker_profile_midoverlap_diagnostic_coordination_receipt.json"
        )
        if str(existing.get("execution_status", "")) == "wave36_speaker_profile_midoverlap_diagnostic_coordination_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "wave36_speaker_profile_midoverlap_diagnostic_coordination_complete",
                "blocker": "attribution_claims_still_blocked",
            }

    card_rows = build_coordination_rows()
    fill_row = build_fill_row(card_rows)
    receipt_row = build_receipt_row(
        wave36_receipt, midoverlap_receipt, wave32_refresh_receipt, lightoverlap_refresh_receipt
    )
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "diagnostic_case_scope": fill_row["diagnostic_case_scope"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write Wave36 speaker profile MidOverlap diagnostic refresh after Wave36 closure."
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
