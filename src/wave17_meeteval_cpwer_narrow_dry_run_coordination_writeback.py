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
    "wave17_closure_status",
    "midoverlap_coordination_status",
    "prior_meeteval_coordination_status",
    "character_level_dry_run_count",
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


def count_character_level_dry_runs() -> str:
    rows = load_json_rows("results/tables/meeteval_cpwer_character_level_official_execution.json")
    count = sum(
        1
        for row in rows
        if str(row.get("execution_status", "")) == "character_level_cpwer_narrow_dry_run_complete"
    )
    return str(count)


def assert_writeback_preconditions(
    wave17_receipt: dict[str, Any],
    midoverlap_receipt: dict[str, Any],
    demo_wave17_fill: dict[str, Any],
    prior_meeteval_receipt: dict[str, Any],
) -> None:
    if str(wave17_receipt.get("execution_status", "")) != "wave17_exploration_baseline_closure_complete":
        raise RuntimeError("Wave17 closure must be complete before MeetEval narrow dry-run refresh coordination")
    if str(midoverlap_receipt.get("execution_status", "")) != "wave17_speaker_profile_midoverlap_diagnostic_coordination_complete":
        raise RuntimeError(
            "Wave17 MidOverlap diagnostic coordination must be complete before MeetEval refresh"
        )
    if str(demo_wave17_fill.get("fill_status", "")) != "writeback_filled":
        raise RuntimeError("Demo Wave17 presentation writeback must be filled before MeetEval coordination")
    if str(demo_wave17_fill.get("storyboard_receipt_status", "")) != "wave17_presentation_extension_complete":
        raise RuntimeError(
            "Demo Wave17 storyboard receipt must be wave17_presentation_extension_complete before MeetEval coordination"
        )
    if str(prior_meeteval_receipt.get("execution_status", "")) != "meeteval_cpwer_narrow_dry_run_coordination_complete":
        raise RuntimeError(
            "Wave10 MeetEval cpWER narrow dry-run coordination must be complete before Wave17 refresh"
        )
    character_count = int(count_character_level_dry_runs())
    if character_count < 5:
        raise RuntimeError(
            f"Character-level narrow dry-run must cover 5/5 gold cases; got {character_count}"
        )
    if not (PROJECT_ROOT / "results/tables/meeteval_cpwer_execution_receipt.json").exists():
        raise RuntimeError("Missing prerequisite artifact: results/tables/meeteval_cpwer_execution_receipt.json")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "character_level_dry_run",
            "headline": "Character-spaced cpWER narrow dry-run remains complete on 5/5 gold cases",
            "artifact_anchor": "results/tables/meeteval_cpwer_character_level_official_execution.json",
            "coordination_note": "experimental/frontier dry-run only; not an official benchmark claim.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "receipt_fill_boundary",
            "headline": "Execution receipt fill documents per-case character-level cpWER",
            "artifact_anchor": "results/tables/meeteval_cpwer_execution_receipt.json",
            "coordination_note": "Receipt fill complete; official benchmark completion still blocked.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "midoverlap_prior",
            "headline": "Wave17 MidOverlap diagnostic coordination precedes MeetEval narrow dry-run refresh",
            "artifact_anchor": "results/figures/wave17_speaker_profile_midoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Speaker-profile diagnostic chain provides slice context only.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave17_boundary",
            "headline": "Wave17 closure keeps MeetEval coordination separate from gold baseline CER",
            "artifact_anchor": "results/figures/wave17_exploration_baseline_closure_card.md",
            "coordination_note": "Coordination writeback only; stable gold CER tables unchanged.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "official_benchmark_boundary",
            "headline": "Narrow dry-run refresh does not upgrade character-level dry-run to official benchmark",
            "artifact_anchor": "results/figures/meeteval_cpwer_narrow_dry_run_coordination_card.md",
            "coordination_note": "Official MeetEval benchmark claims remain blocked.",
            "result_label": "experimental/frontier",
        },
    ]


def build_fill_row(rows: list[dict[str, str]], narrow_dry_run_case_count: str) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "wave17_meeteval_cpwer_narrow_dry_run_coordination_card",
        "coordination_section_count": str(len(rows)),
        "narrow_dry_run_case_count": narrow_dry_run_case_count,
        "execution_receipt_status": "wave17_meeteval_cpwer_narrow_dry_run_coordination_complete",
        "blocker": "official_benchmark_claims_still_blocked",
        "fill_note": (
            "Documented MeetEval character-level narrow dry-run refresh boundary after Wave17 MidOverlap chain; "
            "official benchmark claims remain blocked."
        ),
    }


def build_receipt_row(
    wave17_receipt: dict[str, Any],
    midoverlap_receipt: dict[str, Any],
    prior_meeteval_receipt: dict[str, Any],
    character_count: str,
) -> dict[str, str]:
    return {
        "execution_status": "wave17_meeteval_cpwer_narrow_dry_run_coordination_complete",
        "coordination_scope": "wave17_meeteval_cpwer_narrow_dry_run",
        "wave17_closure_status": str(wave17_receipt.get("execution_status", "")),
        "midoverlap_coordination_status": str(midoverlap_receipt.get("execution_status", "")),
        "prior_meeteval_coordination_status": str(prior_meeteval_receipt.get("execution_status", "")),
        "character_level_dry_run_count": character_count,
        "expected_inputs": (
            "Wave17 closure, MidOverlap diagnostic, demo wave17, Wave10 MeetEval narrow dry-run coordination."
        ),
        "writeback_note": (
            "experimental/frontier coordination only; does not claim official MeetEval benchmark completion."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Wave17 MeetEval cpWER Narrow Dry-Run Coordination Card (experimental/frontier)",
        "",
        "Narrow dry-run refresh boundary coordination — not an official benchmark completion claim.",
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
        "# Wave17 MeetEval cpWER Narrow Dry-Run Coordination Writeback",
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
        "# Wave17 MeetEval cpWER Narrow Dry-Run Coordination Receipt",
        "",
        "| execution_status | character_level_dry_run_count | prior_meeteval_coordination_status |",
        "| --- | ---: | --- |",
        (
            f"| {row['execution_status']} | {row['character_level_dry_run_count']} | "
            f"{row['prior_meeteval_coordination_status']} |"
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

    card_csv = tables_dir / "wave17_meeteval_cpwer_narrow_dry_run_coordination_card.csv"
    card_json = tables_dir / "wave17_meeteval_cpwer_narrow_dry_run_coordination_card.json"
    card_md = figures_dir / "wave17_meeteval_cpwer_narrow_dry_run_coordination_card.md"
    fill_csv = tables_dir / "wave17_meeteval_cpwer_narrow_dry_run_coordination_writeback.csv"
    fill_json = tables_dir / "wave17_meeteval_cpwer_narrow_dry_run_coordination_writeback.json"
    fill_md = figures_dir / "wave17_meeteval_cpwer_narrow_dry_run_coordination_writeback.md"
    receipt_json = tables_dir / "wave17_meeteval_cpwer_narrow_dry_run_coordination_receipt.json"
    receipt_md = figures_dir / "wave17_meeteval_cpwer_narrow_dry_run_coordination_receipt.md"

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
    wave17_receipt = load_json_dict("results/tables/wave17_exploration_baseline_closure_receipt.json")
    midoverlap_receipt = load_json_dict(
        "results/tables/wave17_speaker_profile_midoverlap_diagnostic_coordination_receipt.json"
    )
    demo_wave17_fill = load_json_dict("results/tables/demo_wave17_presentation_writeback.json")
    prior_meeteval_receipt = load_json_dict(
        "results/tables/meeteval_cpwer_narrow_dry_run_coordination_receipt.json"
    )
    assert_writeback_preconditions(
        wave17_receipt, midoverlap_receipt, demo_wave17_fill, prior_meeteval_receipt
    )

    receipt_path = PROJECT_ROOT / "results/tables/wave17_meeteval_cpwer_narrow_dry_run_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict(
            "results/tables/wave17_meeteval_cpwer_narrow_dry_run_coordination_receipt.json"
        )
        if str(existing.get("execution_status", "")) == "wave17_meeteval_cpwer_narrow_dry_run_coordination_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "wave17_meeteval_cpwer_narrow_dry_run_coordination_complete",
                "blocker": "official_benchmark_claims_still_blocked",
            }

    character_count = count_character_level_dry_runs()
    card_rows = build_coordination_rows()
    fill_row = build_fill_row(card_rows, character_count)
    receipt_row = build_receipt_row(
        wave17_receipt, midoverlap_receipt, prior_meeteval_receipt, character_count
    )
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "narrow_dry_run_case_count": fill_row["narrow_dry_run_case_count"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write Wave17 MeetEval cpWER narrow dry-run refresh after Wave17 MidOverlap chain."
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
