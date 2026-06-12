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
    "wave79_closure_status",
    "wave73_lightoverlap_refresh_status",
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
    wave79_receipt: dict[str, Any],
    demo_wave79_fill: dict[str, Any],
    wave73_lightoverlap_receipt: dict[str, Any],
    lightoverlap_receipt: dict[str, Any],
) -> None:
    if str(wave79_receipt.get("execution_status", "")) != "wave79_exploration_baseline_closure_complete":
        raise RuntimeError("Wave79 closure must be complete before LightOverlap diagnostic refresh coordination")
    if str(demo_wave79_fill.get("fill_status", "")) != "writeback_filled":
        raise RuntimeError("Demo Wave79 presentation writeback must be filled before LightOverlap coordination")
    if str(demo_wave79_fill.get("storyboard_receipt_status", "")) != "wave79_presentation_extension_complete":
        raise RuntimeError(
            "Demo Wave79 storyboard receipt must be wave79_presentation_extension_complete before LightOverlap coordination"
        )
    if (
        str(wave73_lightoverlap_receipt.get("execution_status", ""))
        != "wave73_speaker_profile_lightoverlap_diagnostic_coordination_complete"
    ):
        raise RuntimeError(
            "Wave73 LightOverlap diagnostic refresh must be complete before Wave79 refresh coordination"
        )
    if str(lightoverlap_receipt.get("execution_status", "")) != "speaker_profile_lightoverlap_diagnostic_coordination_complete":
        raise RuntimeError(
            "Speaker profile LightOverlap diagnostic coordination must be complete before Wave79 refresh"
        )
    if not (PROJECT_ROOT / "results/figures/separation_phase_diagram.md").exists():
        raise RuntimeError("Missing prerequisite artifact: results/figures/separation_phase_diagram.md")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "lightoverlap_diagnostic_scope",
            "headline": "LightOverlap separation-harm diagnostic scope refresh after Wave79 closure",
            "artifact_anchor": "results/figures/separation_phase_diagram.md",
            "coordination_note": "Separation harms ASR on this gold anchor; diagnostic-only — no attribution claim.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "lightoverlap_prior",
            "headline": "Wave8 LightOverlap diagnostic coordination remains the prerequisite chain",
            "artifact_anchor": "results/figures/speaker_profile_lightoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Wave79 refresh does not replace original LightOverlap boundary documentation.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave73_refresh",
            "headline": "Wave73 LightOverlap diagnostic refresh precedes Wave79 refresh",
            "artifact_anchor": "results/figures/wave73_speaker_profile_lightoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Prior wave refresh provides chain for cyclic overlap diagnostic coordination.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave79_boundary",
            "headline": "Wave79 closure defers overlap embedding execution to diagnostic boundaries only",
            "artifact_anchor": "results/figures/wave79_exploration_baseline_closure_card.md",
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
        "writeback_scope": "wave79_speaker_profile_lightoverlap_diagnostic_coordination_card",
        "coordination_section_count": str(len(rows)),
        "diagnostic_case_scope": "LightOverlap",
        "candidate_case_scope": "MidOverlap",
        "execution_receipt_status": "wave79_speaker_profile_lightoverlap_diagnostic_coordination_complete",
        "blocker": "attribution_claims_still_blocked",
        "fill_note": (
            "Documented LightOverlap diagnostic refresh after Wave79 closure; "
            "no overlap-case embedding execution claimed."
        ),
    }


def build_receipt_row(
    wave79_receipt: dict[str, Any],
    wave73_lightoverlap_receipt: dict[str, Any],
    lightoverlap_receipt: dict[str, Any],
) -> dict[str, str]:
    return {
        "execution_status": "wave79_speaker_profile_lightoverlap_diagnostic_coordination_complete",
        "coordination_scope": "wave79_speaker_profile_lightoverlap_diagnostic",
        "wave79_closure_status": str(wave79_receipt.get("execution_status", "")),
        "wave73_lightoverlap_refresh_status": str(wave73_lightoverlap_receipt.get("execution_status", "")),
        "lightoverlap_prior_coordination_status": str(lightoverlap_receipt.get("execution_status", "")),
        "separation_harm_signal": "separation_hurts_on_lightoverlap",
        "expected_inputs": (
            "Wave79 closure, demo wave79 writeback, Wave73 LightOverlap refresh, and Wave8 LightOverlap coordination."
        ),
        "writeback_note": (
            "experimental/frontier coordination only; does not claim overlap-case embedding execution."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Wave79 Speaker Profile LightOverlap Diagnostic Coordination Card (experimental/frontier)",
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
        "# Wave79 Speaker Profile LightOverlap Diagnostic Coordination Writeback",
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
        "# Wave79 Speaker Profile LightOverlap Diagnostic Coordination Receipt",
        "",
        "| execution_status | wave73_lightoverlap_refresh_status | separation_harm_signal |",
        "| --- | --- | --- |",
        (
            f"| {row['execution_status']} | {row['wave73_lightoverlap_refresh_status']} | "
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

    card_csv = tables_dir / "wave79_speaker_profile_lightoverlap_diagnostic_coordination_card.csv"
    card_json = tables_dir / "wave79_speaker_profile_lightoverlap_diagnostic_coordination_card.json"
    card_md = figures_dir / "wave79_speaker_profile_lightoverlap_diagnostic_coordination_card.md"
    fill_csv = tables_dir / "wave79_speaker_profile_lightoverlap_diagnostic_coordination_writeback.csv"
    fill_json = tables_dir / "wave79_speaker_profile_lightoverlap_diagnostic_coordination_writeback.json"
    fill_md = figures_dir / "wave79_speaker_profile_lightoverlap_diagnostic_coordination_writeback.md"
    receipt_json = tables_dir / "wave79_speaker_profile_lightoverlap_diagnostic_coordination_receipt.json"
    receipt_md = figures_dir / "wave79_speaker_profile_lightoverlap_diagnostic_coordination_receipt.md"

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
    wave79_receipt = load_json_dict("results/tables/wave79_exploration_baseline_closure_receipt.json")
    demo_wave79_fill = load_json_dict("results/tables/demo_wave79_presentation_writeback.json")
    wave73_lightoverlap_receipt = load_json_dict(
        "results/tables/wave73_speaker_profile_lightoverlap_diagnostic_coordination_receipt.json"
    )
    lightoverlap_receipt = load_json_dict(
        "results/tables/speaker_profile_lightoverlap_diagnostic_coordination_receipt.json"
    )
    assert_writeback_preconditions(
        wave79_receipt, demo_wave79_fill, wave73_lightoverlap_receipt, lightoverlap_receipt
    )

    receipt_path = PROJECT_ROOT / "results/tables/wave79_speaker_profile_lightoverlap_diagnostic_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict(
            "results/tables/wave79_speaker_profile_lightoverlap_diagnostic_coordination_receipt.json"
        )
        if str(existing.get("execution_status", "")) == "wave79_speaker_profile_lightoverlap_diagnostic_coordination_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "wave79_speaker_profile_lightoverlap_diagnostic_coordination_complete",
                "blocker": "attribution_claims_still_blocked",
            }

    card_rows = build_coordination_rows()
    fill_row = build_fill_row(card_rows)
    receipt_row = build_receipt_row(wave79_receipt, wave73_lightoverlap_receipt, lightoverlap_receipt)
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "diagnostic_case_scope": fill_row["diagnostic_case_scope"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write Wave79 speaker profile LightOverlap diagnostic refresh after Wave79 closure."
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
