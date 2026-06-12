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
    "phase1_gate_id",
    "execution_receipt_status",
    "blocker",
    "fill_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "coordination_scope",
    "wave9_closure_status",
    "evidence_receipt_coordination_status",
    "midoverlap_diagnostic_status",
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
    wave9_receipt: dict[str, Any],
    evidence_receipt: dict[str, Any],
    midoverlap_receipt: dict[str, Any],
) -> None:
    if str(wave9_receipt.get("execution_status", "")) != "wave9_exploration_baseline_closure_complete":
        raise RuntimeError("Wave9 closure must be complete before phase1 gate coordination")
    if str(evidence_receipt.get("execution_status", "")) != "cascade_benchmark_evidence_receipt_coordination_complete":
        raise RuntimeError("Evidence receipt coordination must be complete before phase1 gate coordination")
    if str(midoverlap_receipt.get("execution_status", "")) != "speaker_profile_midoverlap_diagnostic_coordination_complete":
        raise RuntimeError("MidOverlap diagnostic coordination must be complete before phase1 gate coordination")
    for artifact in (
        "results/tables/cascade_benchmark_manifest_template.json",
        "results/tables/cascade_benchmark_evidence_receipt.json",
    ):
        if not (PROJECT_ROOT / artifact).exists():
            raise RuntimeError(f"Missing prerequisite artifact: {artifact}")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "phase1_gold_gate",
            "headline": "phase1_gold_runtime_foundation is the controlled-timing entry gate",
            "artifact_anchor": "results/tables/cascade_benchmark_manifest_template.csv",
            "coordination_note": "Manifest hardware_label/device fields remain TODO; not executed.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "evidence_receipt_link",
            "headline": "Evidence receipt scaffold aligns with phase1 capture metadata",
            "artifact_anchor": "results/tables/cascade_benchmark_evidence_receipt.json",
            "coordination_note": "collect_controlled_runtime action documented; no session fill claimed.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave9_rollup",
            "headline": "Wave9 speaker diagnostic chain complete before benchmark gate",
            "artifact_anchor": "results/figures/speaker_profile_midoverlap_diagnostic_coordination_card.md",
            "coordination_note": "Diagnostic coordination only; gold CER tables unchanged.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "deployment_boundary",
            "headline": "Controlled timing required before any deployment runtime claims",
            "artifact_anchor": "results/figures/cascade_benchmark_readiness_coordination_card.md",
            "coordination_note": "repo_local_runtime_only boundary preserved for README and demo.",
            "result_label": "qualitative/demo",
        },
    ]


def build_fill_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "cascade_benchmark_phase1_gate_coordination_card",
        "coordination_section_count": str(len(rows)),
        "phase1_gate_id": "phase1_gold_runtime_foundation",
        "execution_receipt_status": "cascade_benchmark_phase1_gate_coordination_complete",
        "blocker": "controlled_benchmark_timing_pending",
        "fill_note": (
            "Filled phase1 gate coordination card after Wave9 MidOverlap diagnostic chain; "
            "controlled hardware timing not executed."
        ),
    }


def build_receipt_row(
    wave9_receipt: dict[str, Any],
    evidence_receipt: dict[str, Any],
    midoverlap_receipt: dict[str, Any],
) -> dict[str, str]:
    return {
        "execution_status": "cascade_benchmark_phase1_gate_coordination_complete",
        "coordination_scope": "wave9_cascade_benchmark_phase1_gate",
        "wave9_closure_status": str(wave9_receipt.get("execution_status", "")),
        "evidence_receipt_coordination_status": str(evidence_receipt.get("execution_status", "")),
        "midoverlap_diagnostic_status": str(midoverlap_receipt.get("execution_status", "")),
        "expected_inputs": (
            "Wave9 closure, evidence receipt coordination, MidOverlap diagnostic, manifest template."
        ),
        "writeback_note": (
            "experimental/frontier coordination only; does not record phase1_gold_runtime_foundation execution."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Cascade Benchmark Phase1 Gate Coordination Card (experimental/frontier)",
        "",
        "Phase1 gate boundary coordination — not a controlled timing execution claim.",
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
        "# Cascade Benchmark Phase1 Gate Coordination Writeback",
        "",
        "| fill_status | phase1_gate_id | execution_receipt_status | blocker |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['fill_status']} | {row['phase1_gate_id']} | "
            f"{row['execution_receipt_status']} | {row['blocker']} |"
        ),
    ]


def build_receipt_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Cascade Benchmark Phase1 Gate Coordination Receipt",
        "",
        "| execution_status | wave9_closure_status | midoverlap_diagnostic_status | blocker |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['execution_status']} | {row['wave9_closure_status']} | "
            f"{row['midoverlap_diagnostic_status']} | controlled_benchmark_timing_pending |"
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

    card_csv = tables_dir / "cascade_benchmark_phase1_gate_coordination_card.csv"
    card_json = tables_dir / "cascade_benchmark_phase1_gate_coordination_card.json"
    card_md = figures_dir / "cascade_benchmark_phase1_gate_coordination_card.md"
    fill_csv = tables_dir / "cascade_benchmark_phase1_gate_coordination_writeback.csv"
    fill_json = tables_dir / "cascade_benchmark_phase1_gate_coordination_writeback.json"
    fill_md = figures_dir / "cascade_benchmark_phase1_gate_coordination_writeback.md"
    receipt_json = tables_dir / "cascade_benchmark_phase1_gate_coordination_receipt.json"
    receipt_md = figures_dir / "cascade_benchmark_phase1_gate_coordination_receipt.md"

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
    evidence_receipt = load_json_dict("results/tables/cascade_benchmark_evidence_receipt_coordination_receipt.json")
    midoverlap_receipt = load_json_dict(
        "results/tables/speaker_profile_midoverlap_diagnostic_coordination_receipt.json"
    )
    assert_writeback_preconditions(wave9_receipt, evidence_receipt, midoverlap_receipt)

    receipt_path = PROJECT_ROOT / "results/tables/cascade_benchmark_phase1_gate_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict("results/tables/cascade_benchmark_phase1_gate_coordination_receipt.json")
        if str(existing.get("execution_status", "")) == "cascade_benchmark_phase1_gate_coordination_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "cascade_benchmark_phase1_gate_coordination_complete",
                "blocker": "controlled_benchmark_timing_pending",
            }

    card_rows = build_coordination_rows()
    fill_row = build_fill_row(card_rows)
    receipt_row = build_receipt_row(wave9_receipt, evidence_receipt, midoverlap_receipt)
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "phase1_gate_id": fill_row["phase1_gate_id"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write cascade benchmark phase1 gate coordination after Wave9 diagnostic chain."
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
