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
    "wave141_closure_status",
    "heavyoverlap_prior_coordination_status",
    "wave135_refresh_status",
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
    wave141_receipt: dict[str, Any],
    demo_wave141_fill: dict[str, Any],
    heavyoverlap_receipt: dict[str, Any],
    wave135_refresh_receipt: dict[str, Any],
    midoverlap_refresh_receipt: dict[str, Any],
) -> None:
    if str(wave141_receipt.get("execution_status", "")) != "wave141_exploration_baseline_closure_complete":
        raise RuntimeError("Wave141 closure must be complete before HeavyOverlap diagnostic refresh coordination")
    if str(demo_wave141_fill.get("fill_status", "")) != "writeback_filled":
        raise RuntimeError("Demo Wave141 presentation writeback must be filled before HeavyOverlap coordination")
    if str(demo_wave141_fill.get("storyboard_receipt_status", "")) != "wave141_presentation_extension_complete":
        raise RuntimeError(
            "Demo Wave141 storyboard receipt must be wave141_presentation_extension_complete before HeavyOverlap coordination"
        )
    if str(heavyoverlap_receipt.get("execution_status", "")) != "speaker_profile_heavyoverlap_diagnostic_coordination_complete":
        raise RuntimeError(
            "Speaker profile HeavyOverlap diagnostic coordination must be complete before Wave141 refresh"
        )
    if (
        str(wave135_refresh_receipt.get("execution_status", ""))
        != "wave135_speaker_profile_heavyoverlap_diagnostic_coordination_complete"
    ):
        raise RuntimeError(
            "Wave135 HeavyOverlap diagnostic refresh must be complete before Wave141 refresh coordination"
        )
    if (
        str(midoverlap_refresh_receipt.get("execution_status", ""))
        != "wave140_speaker_profile_midoverlap_diagnostic_coordination_complete"
    ):
        raise RuntimeError(
            "Wave140 MidOverlap diagnostic refresh must be complete before HeavyOverlap refresh coordination"
        )
    if not (PROJECT_ROOT / "results/figures/separation_phase_diagram.md").exists():
        raise RuntimeError("Missing prerequisite artifact: results/figures/separation_phase_diagram.md")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "heavyoverlap_diagnostic_scope",
            "headline": "HeavyOverlap separation-benefit diagnostic scope refresh after Wave141 closure",
            "artifact_anchor": "results/figures/separation_phase_diagram.md",
            "coordination_note": "Separation helps ASR on this gold anchor; diagnostic-only — no attribution claim.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "heavyoverlap_prior",
            "headline": "Wave12 HeavyOverlap diagnostic coordination remains the prerequisite chain",
            "artifact_anchor": "results/figures/speaker_profile_heavyoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Wave87 refresh does not replace original HeavyOverlap boundary documentation.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave135_refresh",
            "headline": "Wave135 HeavyOverlap diagnostic refresh precedes Wave141 refresh",
            "artifact_anchor": "results/figures/wave135_speaker_profile_heavyoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Prior wave refresh provides chain for cyclic overlap diagnostic coordination.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "midoverlap_refresh",
            "headline": "Wave140 MidOverlap diagnostic refresh precedes HeavyOverlap refresh",
            "artifact_anchor": "results/figures/wave140_speaker_profile_midoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Overlap diagnostic chain progresses MidOverlap → HeavyOverlap through coordinated refreshes.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave141_boundary",
            "headline": "Wave141 closure defers overlap embedding execution to diagnostic boundaries only",
            "artifact_anchor": "results/figures/wave141_exploration_baseline_closure_card.md",
            "coordination_note": "Gold baseline CER tables unchanged; attribution still blocked.",
            "result_label": "experimental/frontier",
        },
    ]


def build_fill_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "wave141_speaker_profile_heavyoverlap_diagnostic_coordination_card",
        "coordination_section_count": str(len(rows)),
        "diagnostic_case_scope": "HeavyOverlap",
        "candidate_case_scope": "OppositeOverlap",
        "execution_receipt_status": "wave141_speaker_profile_heavyoverlap_diagnostic_coordination_complete",
        "blocker": "attribution_claims_still_blocked",
        "fill_note": (
            "Documented HeavyOverlap diagnostic refresh after Wave141 closure; "
            "no overlap-case embedding execution claimed."
        ),
    }


def build_receipt_row(
    wave141_receipt: dict[str, Any],
    heavyoverlap_receipt: dict[str, Any],
    wave135_refresh_receipt: dict[str, Any],
    midoverlap_refresh_receipt: dict[str, Any],
) -> dict[str, str]:
    return {
        "execution_status": "wave141_speaker_profile_heavyoverlap_diagnostic_coordination_complete",
        "coordination_scope": "wave141_speaker_profile_heavyoverlap_diagnostic",
        "wave141_closure_status": str(wave141_receipt.get("execution_status", "")),
        "heavyoverlap_prior_coordination_status": str(heavyoverlap_receipt.get("execution_status", "")),
        "wave135_refresh_status": str(wave135_refresh_receipt.get("execution_status", "")),
        "midoverlap_refresh_status": str(midoverlap_refresh_receipt.get("execution_status", "")),
        "separation_benefit_signal": "separation_helps_on_heavyoverlap",
        "expected_inputs": (
            "Wave141 closure, demo wave141, Wave12 HeavyOverlap, Wave135 refresh, and Wave140 MidOverlap refresh."
        ),
        "writeback_note": (
            "experimental/frontier coordination only; does not claim overlap-case embedding execution."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Wave141 Speaker Profile HeavyOverlap Diagnostic Coordination Card (experimental/frontier)",
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
        "# Wave141 Speaker Profile HeavyOverlap Diagnostic Coordination Writeback",
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
        "# Wave141 Speaker Profile HeavyOverlap Diagnostic Coordination Receipt",
        "",
        "| execution_status | wave135_refresh_status | midoverlap_refresh_status |",
        "| --- | --- | --- |",
        (
            f"| {row['execution_status']} | {row['wave135_refresh_status']} | "
            f"{row['midoverlap_refresh_status']} |"
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

    card_csv = tables_dir / "wave141_speaker_profile_heavyoverlap_diagnostic_coordination_card.csv"
    card_json = tables_dir / "wave141_speaker_profile_heavyoverlap_diagnostic_coordination_card.json"
    card_md = figures_dir / "wave141_speaker_profile_heavyoverlap_diagnostic_coordination_card.md"
    fill_csv = tables_dir / "wave141_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.csv"
    fill_json = tables_dir / "wave141_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.json"
    fill_md = figures_dir / "wave141_speaker_profile_heavyoverlap_diagnostic_coordination_writeback.md"
    receipt_json = tables_dir / "wave141_speaker_profile_heavyoverlap_diagnostic_coordination_receipt.json"
    receipt_md = figures_dir / "wave141_speaker_profile_heavyoverlap_diagnostic_coordination_receipt.md"

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
    wave141_receipt = load_json_dict("results/tables/wave141_exploration_baseline_closure_receipt.json")
    demo_wave141_fill = load_json_dict("results/tables/demo_wave141_presentation_writeback.json")
    heavyoverlap_receipt = load_json_dict(
        "results/tables/speaker_profile_heavyoverlap_diagnostic_coordination_receipt.json"
    )
    wave135_refresh_receipt = load_json_dict(
        "results/tables/wave135_speaker_profile_heavyoverlap_diagnostic_coordination_receipt.json"
    )
    midoverlap_refresh_receipt = load_json_dict(
        "results/tables/wave140_speaker_profile_midoverlap_diagnostic_coordination_receipt.json"
    )
    assert_writeback_preconditions(
        wave141_receipt,
        demo_wave141_fill,
        heavyoverlap_receipt,
        wave135_refresh_receipt,
        midoverlap_refresh_receipt,
    )

    receipt_path = PROJECT_ROOT / "results/tables/wave141_speaker_profile_heavyoverlap_diagnostic_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict(
            "results/tables/wave141_speaker_profile_heavyoverlap_diagnostic_coordination_receipt.json"
        )
        if str(existing.get("execution_status", "")) == "wave141_speaker_profile_heavyoverlap_diagnostic_coordination_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "wave141_speaker_profile_heavyoverlap_diagnostic_coordination_complete",
                "blocker": "attribution_claims_still_blocked",
            }

    card_rows = build_coordination_rows()
    fill_row = build_fill_row(card_rows)
    receipt_row = build_receipt_row(
        wave141_receipt, heavyoverlap_receipt, wave135_refresh_receipt, midoverlap_refresh_receipt
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
        description="Write Wave141 speaker profile HeavyOverlap diagnostic refresh after Wave141 closure."
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
