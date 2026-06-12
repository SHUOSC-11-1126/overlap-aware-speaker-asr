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
    "phase2_gate_id",
    "execution_receipt_status",
    "blocker",
    "fill_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "coordination_scope",
    "wave10_closure_status",
    "phase1_gate_coordination_status",
    "meeteval_coordination_status",
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
    wave10_receipt: dict[str, Any],
    phase1_receipt: dict[str, Any],
    meeteval_receipt: dict[str, Any],
) -> None:
    if str(wave10_receipt.get("execution_status", "")) != "wave10_exploration_baseline_closure_complete":
        raise RuntimeError("Wave10 closure must be complete before phase2 gate coordination")
    if str(phase1_receipt.get("execution_status", "")) != "cascade_benchmark_phase1_gate_coordination_complete":
        raise RuntimeError("Phase1 gate coordination must be complete before phase2 gate coordination")
    if str(meeteval_receipt.get("execution_status", "")) != "meeteval_cpwer_narrow_dry_run_coordination_complete":
        raise RuntimeError("MeetEval narrow dry-run coordination must be complete before phase2 gate coordination")
    if not (PROJECT_ROOT / "results/tables/cascade_benchmark_manifest_template.json").exists():
        raise RuntimeError("Missing prerequisite artifact: results/tables/cascade_benchmark_manifest_template.json")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "phase2_synthetic_gate",
            "headline": "phase2_synthetic_runtime_foundation is the synthetic-split timing entry gate",
            "artifact_anchor": "results/tables/cascade_benchmark_manifest_template.csv",
            "coordination_note": "Follows phase1 gold gate; manifest TODO fields not executed.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "phase1_prerequisite",
            "headline": "Phase1 gold runtime gate coordinated in prior wave",
            "artifact_anchor": "results/figures/cascade_benchmark_phase1_gate_coordination_card.md",
            "coordination_note": "phase1_gold_runtime_foundation template_only; timing not captured.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "meeteval_boundary",
            "headline": "MeetEval narrow dry-run coordinated before synthetic benchmark gate",
            "artifact_anchor": "results/figures/meeteval_cpwer_narrow_dry_run_coordination_card.md",
            "coordination_note": "5/5 character-level dry-run; official benchmark claims still blocked.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave10_boundary",
            "headline": "Wave10 closure keeps phase2 gate separate from gold baseline CER",
            "artifact_anchor": "results/figures/wave10_exploration_baseline_closure_card.md",
            "coordination_note": "Coordination writeback only; no controlled benchmark session claimed.",
            "result_label": "experimental/frontier",
        },
    ]


def build_fill_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "cascade_benchmark_phase2_gate_coordination_card",
        "coordination_section_count": str(len(rows)),
        "phase2_gate_id": "phase2_synthetic_runtime_foundation",
        "execution_receipt_status": "cascade_benchmark_phase2_gate_coordination_complete",
        "blocker": "controlled_benchmark_timing_pending",
        "fill_note": (
            "Filled phase2 gate coordination card after Wave10 MeetEval coordination; "
            "synthetic-split controlled timing not executed."
        ),
    }


def build_receipt_row(
    wave10_receipt: dict[str, Any],
    phase1_receipt: dict[str, Any],
    meeteval_receipt: dict[str, Any],
) -> dict[str, str]:
    return {
        "execution_status": "cascade_benchmark_phase2_gate_coordination_complete",
        "coordination_scope": "wave10_cascade_benchmark_phase2_gate",
        "wave10_closure_status": str(wave10_receipt.get("execution_status", "")),
        "phase1_gate_coordination_status": str(phase1_receipt.get("execution_status", "")),
        "meeteval_coordination_status": str(meeteval_receipt.get("execution_status", "")),
        "expected_inputs": (
            "Wave10 closure, phase1 gate coordination, MeetEval narrow dry-run coordination, manifest template."
        ),
        "writeback_note": (
            "experimental/frontier coordination only; does not record phase2_synthetic_runtime_foundation execution."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Cascade Benchmark Phase2 Gate Coordination Card (experimental/frontier)",
        "",
        "Phase2 gate boundary coordination — not a controlled timing execution claim.",
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
        "# Cascade Benchmark Phase2 Gate Coordination Writeback",
        "",
        "| fill_status | phase2_gate_id | execution_receipt_status | blocker |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['fill_status']} | {row['phase2_gate_id']} | "
            f"{row['execution_receipt_status']} | {row['blocker']} |"
        ),
    ]


def build_receipt_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Cascade Benchmark Phase2 Gate Coordination Receipt",
        "",
        "| execution_status | phase1_gate_coordination_status | meeteval_coordination_status | blocker |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['execution_status']} | {row['phase1_gate_coordination_status']} | "
            f"{row['meeteval_coordination_status']} | controlled_benchmark_timing_pending |"
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

    card_csv = tables_dir / "cascade_benchmark_phase2_gate_coordination_card.csv"
    card_json = tables_dir / "cascade_benchmark_phase2_gate_coordination_card.json"
    card_md = figures_dir / "cascade_benchmark_phase2_gate_coordination_card.md"
    fill_csv = tables_dir / "cascade_benchmark_phase2_gate_coordination_writeback.csv"
    fill_json = tables_dir / "cascade_benchmark_phase2_gate_coordination_writeback.json"
    fill_md = figures_dir / "cascade_benchmark_phase2_gate_coordination_writeback.md"
    receipt_json = tables_dir / "cascade_benchmark_phase2_gate_coordination_receipt.json"
    receipt_md = figures_dir / "cascade_benchmark_phase2_gate_coordination_receipt.md"

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
    wave10_receipt = load_json_dict("results/tables/wave10_exploration_baseline_closure_receipt.json")
    phase1_receipt = load_json_dict("results/tables/cascade_benchmark_phase1_gate_coordination_receipt.json")
    meeteval_receipt = load_json_dict("results/tables/meeteval_cpwer_narrow_dry_run_coordination_receipt.json")
    assert_writeback_preconditions(wave10_receipt, phase1_receipt, meeteval_receipt)

    receipt_path = PROJECT_ROOT / "results/tables/cascade_benchmark_phase2_gate_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict("results/tables/cascade_benchmark_phase2_gate_coordination_receipt.json")
        if str(existing.get("execution_status", "")) == "cascade_benchmark_phase2_gate_coordination_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "cascade_benchmark_phase2_gate_coordination_complete",
                "blocker": "controlled_benchmark_timing_pending",
            }

    card_rows = build_coordination_rows()
    fill_row = build_fill_row(card_rows)
    receipt_row = build_receipt_row(wave10_receipt, phase1_receipt, meeteval_receipt)
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "phase2_gate_id": fill_row["phase2_gate_id"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write cascade benchmark phase2 gate coordination after Wave10 MeetEval chain."
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
