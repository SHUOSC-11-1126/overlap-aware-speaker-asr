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
    "execution_receipt_status",
    "blocker",
    "fill_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "coordination_scope",
    "wave21_closure_status",
    "lightoverlap_coordination_status",
    "demo_wave21_status",
    "frontier_go_count",
    "expected_inputs",
    "writeback_note",
]


def load_json_dict(path_rel: str) -> dict[str, Any]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def assert_closure_preconditions(
    wave21_receipt: dict[str, Any],
    lightoverlap_receipt: dict[str, Any],
    demo_wave21_fill: dict[str, Any],
    frontier_summary: dict[str, Any],
) -> None:
    if str(wave21_receipt.get("execution_status", "")) != "wave21_exploration_baseline_closure_complete":
        raise RuntimeError("Wave21 closure receipt must be complete before Wave22 exploration baseline closure")
    if str(lightoverlap_receipt.get("execution_status", "")) != "wave21_speaker_profile_lightoverlap_diagnostic_coordination_complete":
        raise RuntimeError("Wave21 LightOverlap diagnostic coordination must be complete before Wave22 closure")
    if str(demo_wave21_fill.get("fill_status", "")) != "writeback_filled":
        raise RuntimeError("Demo Wave21 presentation writeback must be filled before Wave22 closure")
    if str(demo_wave21_fill.get("storyboard_receipt_status", "")) != "wave21_presentation_extension_complete":
        raise RuntimeError(
            "Demo Wave21 storyboard receipt must be wave21_presentation_extension_complete before Wave22 closure"
        )
    if str(frontier_summary.get("coordination_state", "")) != "all_ready":
        raise RuntimeError(
            f"Frontier board must be all_ready; got {frontier_summary.get('coordination_state', 'missing')!r}"
        )


def build_closure_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "wave21_rollup",
            "headline": "Wave21 closed: LightOverlap diagnostic refresh + demo + exploration closure",
            "artifact_anchor": "results/figures/wave21_exploration_baseline_closure_card.md",
            "coordination_note": "experimental/frontier coordination only; gold baseline untouched.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "lightoverlap_coordination",
            "headline": "LightOverlap separation-harm diagnostic refresh coordinated after Wave21 closure",
            "artifact_anchor": "results/figures/wave21_speaker_profile_lightoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Diagnostic scope only; attribution claims still blocked.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "demo_wave21",
            "headline": "Demo presentation polish extended to 22 sections under qualitative/demo labeling",
            "artifact_anchor": "results/figures/demo_wave21_presentation_writeback.md",
            "coordination_note": "No live demo or benchmark timing claims.",
            "result_label": "qualitative/demo",
        },
        {
            "section_id": "frontier_board",
            "headline": "Frontier go/no-go board remains all_ready after Wave21 chain",
            "artifact_anchor": "results/tables/frontier_go_no_go_summary.json",
            "coordination_note": "Coordination receipts only; no deployable routing claims.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave22_boundary",
            "headline": "Speaker profile MidOverlap diagnostic refresh is the next open experimental coordination gate",
            "artifact_anchor": "results/tables/speaker_profile_status.json",
            "coordination_note": "Wave22 closure does not record overlap-case embedding execution sessions.",
            "result_label": "experimental/frontier",
        },
    ]


def build_fill_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "wave22_exploration_baseline_closure_card",
        "coordination_section_count": str(len(rows)),
        "execution_receipt_status": "wave22_exploration_baseline_closure_complete",
        "blocker": "controlled_benchmark_timing_pending",
        "fill_note": (
            "Wave22 exploration+baseline closure rollup after Wave21 chain; stable gold baseline preserved."
        ),
    }


def build_receipt_row(
    wave21_receipt: dict[str, Any],
    lightoverlap_receipt: dict[str, Any],
    demo_wave21_fill: dict[str, Any],
    frontier_summary: dict[str, Any],
) -> dict[str, str]:
    return {
        "execution_status": "wave22_exploration_baseline_closure_complete",
        "coordination_scope": "wave22_exploration_baseline",
        "wave21_closure_status": str(wave21_receipt.get("execution_status", "")),
        "lightoverlap_coordination_status": str(lightoverlap_receipt.get("execution_status", "")),
        "demo_wave21_status": str(demo_wave21_fill.get("storyboard_receipt_status", "")),
        "frontier_go_count": str(frontier_summary.get("go_count", "")),
        "expected_inputs": (
            "Wave21 closure, LightOverlap diagnostic, demo wave21, frontier summary."
        ),
        "writeback_note": (
            "探索+基线 Wave22 closure writeback; qualitative/demo and experimental/frontier labels preserved."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Wave22 Exploration+Baseline Closure Card",
        "",
        "Coordination closure — not a benchmark or live-demo completion claim.",
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
        "# Wave22 Exploration+Baseline Closure Writeback",
        "",
        "| fill_status | coordination_section_count | execution_receipt_status | blocker |",
        "| --- | ---: | --- | --- |",
        (
            f"| {row['fill_status']} | {row['coordination_section_count']} | "
            f"{row['execution_receipt_status']} | {row['blocker']} |"
        ),
    ]


def build_receipt_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Wave22 Exploration+Baseline Closure Receipt",
        "",
        "| execution_status | wave21_closure_status | frontier_go_count |",
        "| --- | --- | ---: |",
        (
            f"| {row['execution_status']} | {row['wave21_closure_status']} | {row['frontier_go_count']} |"
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

    card_csv = tables_dir / "wave22_exploration_baseline_closure_card.csv"
    card_json = tables_dir / "wave22_exploration_baseline_closure_card.json"
    card_md = figures_dir / "wave22_exploration_baseline_closure_card.md"
    fill_csv = tables_dir / "wave22_exploration_baseline_closure_writeback.csv"
    fill_json = tables_dir / "wave22_exploration_baseline_closure_writeback.json"
    fill_md = figures_dir / "wave22_exploration_baseline_closure_writeback.md"
    receipt_json = tables_dir / "wave22_exploration_baseline_closure_receipt.json"
    receipt_md = figures_dir / "wave22_exploration_baseline_closure_receipt.md"

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


def run_closure_writeback(force: bool = False) -> dict[str, str]:
    wave21_receipt = load_json_dict("results/tables/wave21_exploration_baseline_closure_receipt.json")
    lightoverlap_receipt = load_json_dict(
        "results/tables/wave21_speaker_profile_lightoverlap_diagnostic_coordination_receipt.json"
    )
    demo_wave21_fill = load_json_dict("results/tables/demo_wave21_presentation_writeback.json")
    frontier_summary = load_json_dict("results/tables/frontier_go_no_go_summary.json")
    assert_closure_preconditions(wave21_receipt, lightoverlap_receipt, demo_wave21_fill, frontier_summary)

    receipt_path = PROJECT_ROOT / "results/tables/wave22_exploration_baseline_closure_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict("results/tables/wave22_exploration_baseline_closure_receipt.json")
        if str(existing.get("execution_status", "")) == "wave22_exploration_baseline_closure_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "wave22_exploration_baseline_closure_complete",
                "blocker": "controlled_benchmark_timing_pending",
            }

    card_rows = build_closure_rows()
    fill_row = build_fill_row(card_rows)
    receipt_row = build_receipt_row(wave21_receipt, lightoverlap_receipt, demo_wave21_fill, frontier_summary)
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "coordination_section_count": fill_row["coordination_section_count"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write Wave22 exploration+baseline closure after Wave21 chain.")
    parser.add_argument("--force", action="store_true", help="Overwrite an already-filled closure receipt.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_closure_writeback(force=args.force)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
