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
    "wave11_closure_status",
    "phase3_gate_coordination_status",
    "external_coordination_status",
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
    wave11_receipt: dict[str, Any],
    phase3_receipt: dict[str, Any],
    external_receipt: dict[str, Any],
    demo_wave11_fill: dict[str, Any],
    frontier_summary: dict[str, Any],
) -> None:
    if str(wave11_receipt.get("execution_status", "")) != "wave11_exploration_baseline_closure_complete":
        raise RuntimeError("Wave11 closure receipt must be complete before Wave12 exploration baseline closure")
    if str(phase3_receipt.get("execution_status", "")) != "cascade_benchmark_phase3_gate_coordination_complete":
        raise RuntimeError("Cascade benchmark phase3 gate coordination must be complete before Wave12 closure")
    if str(external_receipt.get("execution_status", "")) != "external_validation_narrow_slice_coordination_complete":
        raise RuntimeError("External validation narrow slice coordination must be complete before Wave12 closure")
    if str(demo_wave11_fill.get("fill_status", "")) != "writeback_filled":
        raise RuntimeError("Demo Wave11 presentation writeback must be filled before Wave12 closure")
    if str(frontier_summary.get("coordination_state", "")) != "all_ready":
        raise RuntimeError(
            f"Frontier board must be all_ready; got {frontier_summary.get('coordination_state', 'missing')!r}"
        )


def build_closure_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "wave11_rollup",
            "headline": "Wave11 closed: external validation + phase3 gate + demo + exploration closure",
            "artifact_anchor": "results/figures/wave11_exploration_baseline_closure_card.md",
            "coordination_note": "experimental/frontier coordination only; gold baseline untouched.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "external_validation",
            "headline": "External AISHELL-4 narrow slice coordination complete",
            "artifact_anchor": "results/figures/external_validation_narrow_slice_coordination_card.md",
            "coordination_note": "external/sanity-check only; gold benchmark claims still blocked.",
            "result_label": "external/sanity-check",
        },
        {
            "section_id": "phase3_gate_boundary",
            "headline": "Benchmark phase3 gold surface refresh gate coordinated; refresh not executed",
            "artifact_anchor": "results/figures/cascade_benchmark_phase3_gate_coordination_card.md",
            "coordination_note": "phase3_gold_surface_refresh template_only.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "frontier_all_ready",
            "headline": "Five-track frontier board remains 5/5 go",
            "artifact_anchor": "results/tables/frontier_go_no_go_summary.json",
            "coordination_note": "Coordination rollup; does not claim frontier execution completion.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave12_boundary",
            "headline": "Controlled cascade benchmark timing remains the primary open experimental gate",
            "artifact_anchor": "results/tables/cascade_benchmark_manifest_template.csv",
            "coordination_note": "Wave12 closure does not record controlled hardware benchmark sessions.",
            "result_label": "experimental/frontier",
        },
    ]


def build_fill_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "wave12_exploration_baseline_closure_card",
        "coordination_section_count": str(len(rows)),
        "execution_receipt_status": "wave12_exploration_baseline_closure_complete",
        "blocker": "controlled_benchmark_timing_pending",
        "fill_note": (
            "Wave12 exploration+baseline closure rollup after Wave11 chain; stable gold baseline preserved."
        ),
    }


def build_receipt_row(
    wave11_receipt: dict[str, Any],
    phase3_receipt: dict[str, Any],
    external_receipt: dict[str, Any],
    frontier_summary: dict[str, Any],
) -> dict[str, str]:
    return {
        "execution_status": "wave12_exploration_baseline_closure_complete",
        "coordination_scope": "wave12_exploration_baseline",
        "wave11_closure_status": str(wave11_receipt.get("execution_status", "")),
        "phase3_gate_coordination_status": str(phase3_receipt.get("execution_status", "")),
        "external_coordination_status": str(external_receipt.get("execution_status", "")),
        "frontier_go_count": str(frontier_summary.get("go_count", "")),
        "expected_inputs": (
            "Wave11 closure, phase3 gate coordination, external validation coordination, demo wave11, frontier summary."
        ),
        "writeback_note": (
            "探索+基线 Wave12 closure writeback; qualitative/demo and experimental/frontier labels preserved."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Wave12 Exploration+Baseline Closure Card",
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
        "# Wave12 Exploration+Baseline Closure Writeback",
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
        "# Wave12 Exploration+Baseline Closure Receipt",
        "",
        "| execution_status | wave11_closure_status | frontier_go_count |",
        "| --- | --- | ---: |",
        (
            f"| {row['execution_status']} | {row['wave11_closure_status']} | {row['frontier_go_count']} |"
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

    card_csv = tables_dir / "wave12_exploration_baseline_closure_card.csv"
    card_json = tables_dir / "wave12_exploration_baseline_closure_card.json"
    card_md = figures_dir / "wave12_exploration_baseline_closure_card.md"
    fill_csv = tables_dir / "wave12_exploration_baseline_closure_writeback.csv"
    fill_json = tables_dir / "wave12_exploration_baseline_closure_writeback.json"
    fill_md = figures_dir / "wave12_exploration_baseline_closure_writeback.md"
    receipt_json = tables_dir / "wave12_exploration_baseline_closure_receipt.json"
    receipt_md = figures_dir / "wave12_exploration_baseline_closure_receipt.md"

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
    wave11_receipt = load_json_dict("results/tables/wave11_exploration_baseline_closure_receipt.json")
    phase3_receipt = load_json_dict("results/tables/cascade_benchmark_phase3_gate_coordination_receipt.json")
    external_receipt = load_json_dict("results/tables/external_validation_narrow_slice_coordination_receipt.json")
    demo_wave11_fill = load_json_dict("results/tables/demo_wave11_presentation_writeback.json")
    frontier_summary = load_json_dict("results/tables/frontier_go_no_go_summary.json")
    assert_closure_preconditions(
        wave11_receipt, phase3_receipt, external_receipt, demo_wave11_fill, frontier_summary
    )

    receipt_path = PROJECT_ROOT / "results/tables/wave12_exploration_baseline_closure_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict("results/tables/wave12_exploration_baseline_closure_receipt.json")
        if str(existing.get("execution_status", "")) == "wave12_exploration_baseline_closure_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "wave12_exploration_baseline_closure_complete",
                "blocker": "controlled_benchmark_timing_pending",
            }

    card_rows = build_closure_rows()
    fill_row = build_fill_row(card_rows)
    receipt_row = build_receipt_row(wave11_receipt, phase3_receipt, external_receipt, frontier_summary)
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "coordination_section_count": fill_row["coordination_section_count"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write Wave12 exploration+baseline closure after Wave11 chain.")
    parser.add_argument("--force", action="store_true", help="Overwrite an already-filled closure receipt.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_closure_writeback(force=args.force)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
