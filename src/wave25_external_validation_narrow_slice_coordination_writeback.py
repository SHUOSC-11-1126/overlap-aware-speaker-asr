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
    "narrow_slice_id",
    "execution_receipt_status",
    "blocker",
    "fill_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "coordination_scope",
    "wave25_closure_status",
    "oppositeoverlap_coordination_status",
    "wave19_refresh_status",
    "narrow_asr_eval_status",
    "external_board_state",
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
    wave25_receipt: dict[str, Any],
    oppositeoverlap_receipt: dict[str, Any],
    demo_wave25_fill: dict[str, Any],
    narrow_eval_receipt: dict[str, Any],
    external_summary: dict[str, Any],
    prior_coord_receipt: dict[str, Any],
) -> None:
    if str(wave25_receipt.get("execution_status", "")) != "wave25_exploration_baseline_closure_complete":
        raise RuntimeError("Wave25 closure must be complete before external validation narrow slice coordination")
    if str(oppositeoverlap_receipt.get("execution_status", "")) != "wave24_speaker_profile_oppositeoverlap_diagnostic_coordination_complete":
        raise RuntimeError(
            "Wave24 OppositeOverlap diagnostic coordination must be complete before external validation coordination"
        )
    if str(demo_wave25_fill.get("fill_status", "")) != "writeback_filled":
        raise RuntimeError("Demo Wave25 presentation writeback must be filled before external validation coordination")
    if str(demo_wave25_fill.get("storyboard_receipt_status", "")) != "wave25_presentation_extension_complete":
        raise RuntimeError(
            "Demo Wave25 storyboard receipt must be wave25_presentation_extension_complete before external coordination"
        )
    if str(narrow_eval_receipt.get("execution_status", "")) != "narrow_asr_complete":
        raise RuntimeError(
            f"External narrow ASR eval receipt must be narrow_asr_complete; "
            f"got {narrow_eval_receipt.get('execution_status', 'missing')!r}"
        )
    if str(external_summary.get("overall_state", "")) != "ready_for_narrow_audio_eval":
        raise RuntimeError(
            f"External validation board must be ready_for_narrow_audio_eval; "
            f"got {external_summary.get('overall_state', 'missing')!r}"
        )
    if str(prior_coord_receipt.get("execution_status", "")) != "wave19_external_validation_narrow_slice_coordination_complete":
        raise RuntimeError(
            "Wave19 external validation narrow slice coordination must be complete before Wave25 refresh"
        )
    if not (PROJECT_ROOT / "results/tables/external_validation_slice_mapping.json").exists():
        raise RuntimeError("Missing prerequisite artifact: results/tables/external_validation_slice_mapping.json")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "narrow_asr_receipt",
            "headline": "AISHELL-4 stub slice narrow ASR eval receipt remains filled",
            "artifact_anchor": "results/tables/external_validation_narrow_audio_eval_receipt.json",
            "coordination_note": "external/sanity-check only; whisper-tiny on single excerpt stub.",
            "result_label": "external/sanity-check",
        },
        {
            "section_id": "license_boundary",
            "headline": "License confirmation scaffold gates any README external claim",
            "artifact_anchor": "results/figures/external_validation_license_confirmation.md",
            "coordination_note": "CC BY-SA research confirmation recorded; no gold benchmark upgrade.",
            "result_label": "external/sanity-check",
        },
        {
            "section_id": "wave19_prior_coordination",
            "headline": "Wave19 external validation narrow slice coordination precedes Wave25 refresh",
            "artifact_anchor": "results/figures/wave19_external_validation_narrow_slice_coordination_card.md",
            "coordination_note": "Wave25 refresh does not replace Wave19 external/sanity-check boundary.",
            "result_label": "external/sanity-check",
        },
        {
            "section_id": "oppositeoverlap_prior",
            "headline": "Wave24 OppositeOverlap diagnostic coordination precedes external validation refresh",
            "artifact_anchor": "results/figures/wave24_speaker_profile_oppositeoverlap_diagnostic_coordination_card.md",
            "coordination_note": "experimental/frontier diagnostic chain provides slice context only.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave25_boundary",
            "headline": "Wave25 closure keeps external validation separate from gold baseline CER",
            "artifact_anchor": "results/figures/wave25_exploration_baseline_closure_card.md",
            "coordination_note": "Coordination writeback only; README must keep external/sanity-check labeling.",
            "result_label": "experimental/frontier",
        },
    ]


def build_fill_row(rows: list[dict[str, str]], slice_id: str) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "wave25_external_validation_narrow_slice_coordination_card",
        "coordination_section_count": str(len(rows)),
        "narrow_slice_id": slice_id,
        "execution_receipt_status": "wave25_external_validation_narrow_slice_coordination_complete",
        "blocker": "gold_benchmark_claims_still_blocked",
        "fill_note": (
            "Documented external validation narrow slice refresh boundary after Wave24 OppositeOverlap chain; "
            "gold benchmark claims remain blocked."
        ),
    }


def build_receipt_row(
    wave25_receipt: dict[str, Any],
    oppositeoverlap_receipt: dict[str, Any],
    prior_coord_receipt: dict[str, Any],
    narrow_eval_receipt: dict[str, Any],
    external_summary: dict[str, Any],
) -> dict[str, str]:
    return {
        "execution_status": "wave25_external_validation_narrow_slice_coordination_complete",
        "coordination_scope": "wave25_external_validation_narrow_slice",
        "wave25_closure_status": str(wave25_receipt.get("execution_status", "")),
        "oppositeoverlap_coordination_status": str(oppositeoverlap_receipt.get("execution_status", "")),
        "wave19_refresh_status": str(prior_coord_receipt.get("execution_status", "")),
        "narrow_asr_eval_status": str(narrow_eval_receipt.get("execution_status", "")),
        "external_board_state": str(external_summary.get("overall_state", "")),
        "expected_inputs": (
            "Wave25 closure, OppositeOverlap diagnostic, demo wave25, narrow ASR eval receipt, external board."
        ),
        "writeback_note": (
            "external/sanity-check coordination only; does not claim gold CER or full external benchmark completion."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Wave25 External Validation Narrow Slice Coordination Card (external/sanity-check)",
        "",
        "Narrow slice refresh boundary coordination — not a gold benchmark completion claim.",
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
        "# Wave25 External Validation Narrow Slice Coordination Writeback",
        "",
        "| fill_status | narrow_slice_id | execution_receipt_status | blocker |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['fill_status']} | {row['narrow_slice_id']} | "
            f"{row['execution_receipt_status']} | {row['blocker']} |"
        ),
    ]


def build_receipt_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Wave25 External Validation Narrow Slice Coordination Receipt",
        "",
        "| execution_status | narrow_asr_eval_status | external_board_state | blocker |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['execution_status']} | {row['narrow_asr_eval_status']} | "
            f"{row['external_board_state']} | gold_benchmark_claims_still_blocked |"
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

    card_csv = tables_dir / "wave25_external_validation_narrow_slice_coordination_card.csv"
    card_json = tables_dir / "wave25_external_validation_narrow_slice_coordination_card.json"
    card_md = figures_dir / "wave25_external_validation_narrow_slice_coordination_card.md"
    fill_csv = tables_dir / "wave25_external_validation_narrow_slice_coordination_writeback.csv"
    fill_json = tables_dir / "wave25_external_validation_narrow_slice_coordination_writeback.json"
    fill_md = figures_dir / "wave25_external_validation_narrow_slice_coordination_writeback.md"
    receipt_json = tables_dir / "wave25_external_validation_narrow_slice_coordination_receipt.json"
    receipt_md = figures_dir / "wave25_external_validation_narrow_slice_coordination_receipt.md"

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
    wave25_receipt = load_json_dict("results/tables/wave25_exploration_baseline_closure_receipt.json")
    oppositeoverlap_receipt = load_json_dict(
        "results/tables/wave24_speaker_profile_oppositeoverlap_diagnostic_coordination_receipt.json"
    )
    demo_wave25_fill = load_json_dict("results/tables/demo_wave25_presentation_writeback.json")
    narrow_eval_receipt = load_json_dict("results/tables/external_validation_narrow_audio_eval_receipt.json")
    external_summary = load_json_dict("results/tables/external_validation_go_no_go_summary.json")
    prior_coord_receipt = load_json_dict(
        "results/tables/wave19_external_validation_narrow_slice_coordination_receipt.json"
    )
    assert_writeback_preconditions(
        wave25_receipt,
        oppositeoverlap_receipt,
        demo_wave25_fill,
        narrow_eval_receipt,
        external_summary,
        prior_coord_receipt,
    )

    receipt_path = PROJECT_ROOT / "results/tables/wave25_external_validation_narrow_slice_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict("results/tables/wave25_external_validation_narrow_slice_coordination_receipt.json")
        if str(existing.get("execution_status", "")) == "wave25_external_validation_narrow_slice_coordination_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "wave25_external_validation_narrow_slice_coordination_complete",
                "blocker": "gold_benchmark_claims_still_blocked",
            }

    slice_id = str(narrow_eval_receipt.get("slice_id", "aishell4_meeting_excerpt_stub_001"))
    card_rows = build_coordination_rows()
    fill_row = build_fill_row(card_rows, slice_id)
    receipt_row = build_receipt_row(
        wave25_receipt, oppositeoverlap_receipt, prior_coord_receipt, narrow_eval_receipt, external_summary
    )
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "narrow_slice_id": fill_row["narrow_slice_id"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write Wave25 external validation narrow slice coordination after OppositeOverlap chain."
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
