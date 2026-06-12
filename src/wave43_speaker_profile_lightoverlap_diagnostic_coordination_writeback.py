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
    "wave43_closure_status",
    "wave39_lightoverlap_refresh_status",
    "lightoverlap_prior_coordination_status",
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
    wave43_receipt: dict[str, Any],
    demo_wave43_fill: dict[str, Any],
    wave39_lightoverlap_receipt: dict[str, Any],
    lightoverlap_receipt: dict[str, Any],
) -> None:
    if str(wave43_receipt.get("execution_status", "")) != "wave43_exploration_baseline_closure_complete":
        raise RuntimeError("Wave43 closure must be complete before LightOverlap diagnostic refresh coordination")
    if str(demo_wave43_fill.get("fill_status", "")) != "writeback_filled":
        raise RuntimeError("Demo Wave43 presentation writeback must be filled before LightOverlap coordination")
    if str(demo_wave43_fill.get("storyboard_receipt_status", "")) != "wave43_presentation_extension_complete":
        raise RuntimeError(
            "Demo Wave43 storyboard receipt must be wave43_presentation_extension_complete before LightOverlap coordination"
        )
    if (
        str(wave39_lightoverlap_receipt.get("execution_status", ""))
        != "wave39_speaker_profile_lightoverlap_diagnostic_coordination_complete"
    ):
        raise RuntimeError(
            "Wave39 LightOverlap diagnostic refresh must be complete before Wave43 refresh coordination"
        )
    if str(lightoverlap_receipt.get("execution_status", "")) != "speaker_profile_lightoverlap_diagnostic_coordination_complete":
        raise RuntimeError(
            "Speaker profile LightOverlap diagnostic coordination must be complete before Wave43 refresh"
        )
    if not (PROJECT_ROOT / "results/figures/separation_phase_diagram.md").exists():
        raise RuntimeError("Missing prerequisite artifact: results/figures/separation_phase_diagram.md")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "lightoverlap_diagnostic_scope",
            "headline": "LightOverlap separation-harm diagnostic scope refresh after Wave43 closure",
            "artifact_anchor": "results/figures/separation_phase_diagram.md",
            "coordination_note": "Separation harms ASR on this gold anchor; diagnostic-only — no attribution claim.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "lightoverlap_prior",
            "headline": "Wave8 LightOverlap diagnostic coordination remains the prerequisite chain",
            "artifact_anchor": "results/figures/speaker_profile_lightoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Wave43 refresh does not replace original LightOverlap boundary documentation.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave39_refresh",
            "headline": "Wave39 LightOverlap diagnostic refresh precedes Wave43 refresh",
            "artifact_anchor": "results/figures/wave39_speaker_profile_lightoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Prior wave refresh provides chain for cyclic overlap diagnostic coordination.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave43_boundary",
            "headline": "Wave43 closure defers overlap embedding execution to diagnostic boundaries only",
            "artifact_anchor": "results/figures/wave43_exploration_baseline_closure_card.md",
            "coordination_note": "Gold baseline CER tables unchanged; attribution still blocked.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "attribution_boundary",
            "headline": "LightOverlap refresh does not upgrade diagnostic scope to attribution claims",
            "artifact_anchor": "results/figures/speaker_profile_go_no_go_summary.md",
            "coordination_note": "Controlled benchmark timing required before separation-benefit attribution.",
            "result_label": "experimental/frontier",
        },
    ]


def build_fill_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "wave43_speaker_profile_lightoverlap_diagnostic_coordination_card",
        "coordination_section_count": str(len(rows)),
        "diagnostic_case_scope": "LightOverlap",
        "candidate_case_scope": "MidOverlap",
        "execution_receipt_status": "wave43_speaker_profile_lightoverlap_diagnostic_coordination_complete",
        "blocker": "attribution_claims_still_blocked",
        "fill_note": (
            "Documented LightOverlap diagnostic refresh after Wave43 closure; "
            "no overlap-case embedding execution claimed."
        ),
    }


def build_receipt_row(
    wave43_receipt: dict[str, Any],
    wave39_lightoverlap_receipt: dict[str, Any],
    lightoverlap_receipt: dict[str, Any],
) -> dict[str, str]:
    return {
        "execution_status": "wave43_speaker_profile_lightoverlap_diagnostic_coordination_complete",
        "coordination_scope": "wave43_speaker_profile_lightoverlap_diagnostic",
        "wave43_closure_status": str(wave43_receipt.get("execution_status", "")),
        "wave39_lightoverlap_refresh_status": str(wave39_lightoverlap_receipt.get("execution_status", "")),
        "lightoverlap_prior_coordination_status": str(lightoverlap_receipt.get("execution_status", "")),
        "separation_harm_signal": "separation_hurts_on_lightoverlap",
        "expected_inputs": (
            "Wave43 closure, demo wave43 writeback, Wave39 LightOverlap refresh, and Wave8 LightOverlap coordination."
        ),
        "writeback_note": (
            "experimental/frontier coordination only; does not claim overlap-case embedding execution."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Wave43 Speaker Profile LightOverlap Diagnostic Coordination Card (experimental/frontier)",
        "",
        "LightOverlap diagnostic refresh — not an embedding execution or attribution claim.",
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
        "# Wave43 Speaker Profile LightOverlap Diagnostic Coordination Writeback",
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
        "# Wave43 Speaker Profile LightOverlap Diagnostic Coordination Receipt",
        "",
        "| execution_status | wave39_lightoverlap_refresh_status | separation_harm_signal |",
        "| --- | --- | --- |",
        (
            f"| {row['execution_status']} | {row['wave39_lightoverlap_refresh_status']} | "
            f"{row['separation_harm_signal']} |"
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

    card_csv = tables_dir / "wave43_speaker_profile_lightoverlap_diagnostic_coordination_card.csv"
    card_json = tables_dir / "wave43_speaker_profile_lightoverlap_diagnostic_coordination_card.json"
    card_md = figures_dir / "wave43_speaker_profile_lightoverlap_diagnostic_coordination_card.md"
    fill_csv = tables_dir / "wave43_speaker_profile_lightoverlap_diagnostic_coordination_writeback.csv"
    fill_json = tables_dir / "wave43_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json"
    fill_md = figures_dir / "wave43_speaker_profile_lightoverlap_diagnostic_coordination_writeback.md"
    receipt_json = tables_dir / "wave43_speaker_profile_lightoverlap_diagnostic_coordination_receipt.json"
    receipt_md = figures_dir / "wave43_speaker_profile_lightoverlap_diagnostic_coordination_receipt.md"

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
    wave43_receipt = load_json_dict("results/tables/wave43_exploration_baseline_closure_receipt.json")
    demo_wave43_fill = load_json_dict("results/tables/demo_wave43_presentation_writeback.json")
    wave39_lightoverlap_receipt = load_json_dict(
        "results/tables/wave39_speaker_profile_lightoverlap_diagnostic_coordination_receipt.json"
    )
    lightoverlap_receipt = load_json_dict(
        "results/tables/speaker_profile_lightoverlap_diagnostic_coordination_receipt.json"
    )
    assert_writeback_preconditions(
        wave43_receipt, demo_wave43_fill, wave39_lightoverlap_receipt, lightoverlap_receipt
    )

    receipt_path = PROJECT_ROOT / "results/tables/wave43_speaker_profile_lightoverlap_diagnostic_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict(
            "results/tables/wave43_speaker_profile_lightoverlap_diagnostic_coordination_receipt.json"
        )
        if str(existing.get("execution_status", "")) == "wave43_speaker_profile_lightoverlap_diagnostic_coordination_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "wave43_speaker_profile_lightoverlap_diagnostic_coordination_complete",
                "blocker": "attribution_claims_still_blocked",
            }

    card_rows = build_coordination_rows()
    fill_row = build_fill_row(card_rows)
    receipt_row = build_receipt_row(wave43_receipt, wave39_lightoverlap_receipt, lightoverlap_receipt)
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "diagnostic_case_scope": fill_row["diagnostic_case_scope"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write Wave43 speaker profile LightOverlap diagnostic refresh after Wave43 closure."
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
