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
    "evidence_receipt_step_count",
    "execution_receipt_status",
    "blocker",
    "fill_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "coordination_scope",
    "wave8_closure_status",
    "manifest_coordination_status",
    "phase1_gate_status",
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


def count_evidence_receipt_steps() -> str:
    rows = load_json_rows("results/tables/cascade_benchmark_evidence_receipt.json")
    return str(len(rows)) if rows else "1"


def assert_writeback_preconditions(
    wave8_receipt: dict[str, Any],
    manifest_receipt: dict[str, Any],
    lightoverlap_receipt: dict[str, Any],
) -> None:
    if str(wave8_receipt.get("execution_status", "")) != "wave8_exploration_baseline_closure_complete":
        raise RuntimeError("Wave8 closure must be complete before evidence receipt coordination")
    if str(manifest_receipt.get("execution_status", "")) != "cascade_benchmark_manifest_coordination_complete":
        raise RuntimeError("Cascade benchmark manifest coordination must be complete before evidence receipt coordination")
    if str(lightoverlap_receipt.get("execution_status", "")) != "speaker_profile_lightoverlap_diagnostic_coordination_complete":
        raise RuntimeError(
            "Speaker profile LightOverlap diagnostic coordination must be complete before evidence receipt coordination"
        )
    evidence_path = PROJECT_ROOT / "results/tables/cascade_benchmark_evidence_receipt.json"
    if not evidence_path.exists():
        raise RuntimeError("Missing prerequisite artifact: results/tables/cascade_benchmark_evidence_receipt.json")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "evidence_receipt_scaffold",
            "headline": "Benchmark evidence receipt awaits phase1_gold_runtime_foundation fill",
            "artifact_anchor": "results/tables/cascade_benchmark_evidence_receipt.json",
            "coordination_note": "Template-only scaffold; controlled hardware metadata not recorded.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "manifest_link",
            "headline": "Manifest template phase1 gate aligns with evidence receipt step",
            "artifact_anchor": "results/tables/cascade_benchmark_manifest_template.csv",
            "coordination_note": "Manifest TODO fields must be filled during controlled timing capture only.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "readiness_boundary",
            "headline": "Wave6 readiness coordination defers timing claims to evidence boundary",
            "artifact_anchor": "results/figures/cascade_benchmark_readiness_coordination_card.md",
            "coordination_note": "repo_local_runtime_only — do not mix with stable gold CER tables.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave8_boundary",
            "headline": "Wave8 closure keeps evidence coordination separate from gold baseline",
            "artifact_anchor": "results/figures/wave8_exploration_baseline_closure_card.md",
            "coordination_note": "Coordination writeback only; no benchmark session execution claimed.",
            "result_label": "experimental/frontier",
        },
    ]


def build_fill_row(rows: list[dict[str, str]], evidence_step_count: str) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "cascade_benchmark_evidence_receipt_coordination_card",
        "coordination_section_count": str(len(rows)),
        "evidence_receipt_step_count": evidence_step_count,
        "execution_receipt_status": "cascade_benchmark_evidence_receipt_coordination_complete",
        "blocker": "controlled_benchmark_timing_pending",
        "fill_note": (
            "Filled cascade benchmark evidence receipt coordination card after Wave8 manifest boundary; "
            "phase1_gold_runtime_foundation not executed."
        ),
    }


def build_receipt_row(
    wave8_receipt: dict[str, Any],
    manifest_receipt: dict[str, Any],
    evidence_step_count: str,
) -> dict[str, str]:
    return {
        "execution_status": "cascade_benchmark_evidence_receipt_coordination_complete",
        "coordination_scope": "wave8_cascade_benchmark_evidence_receipt",
        "wave8_closure_status": str(wave8_receipt.get("execution_status", "")),
        "manifest_coordination_status": str(manifest_receipt.get("execution_status", "")),
        "phase1_gate_status": "template_only_not_executed",
        "expected_inputs": (
            "Cascade benchmark evidence receipt scaffold, manifest coordination receipt, and Wave8 closure."
        ),
        "writeback_note": (
            "experimental/frontier coordination only; does not record controlled benchmark session metadata."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Cascade Benchmark Evidence Receipt Coordination Card (experimental/frontier)",
        "",
        "Evidence receipt boundary coordination — not a controlled timing execution claim.",
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
        "# Cascade Benchmark Evidence Receipt Coordination Writeback",
        "",
        "| fill_status | evidence_receipt_step_count | execution_receipt_status | blocker |",
        "| --- | ---: | --- | --- |",
        (
            f"| {row['fill_status']} | {row['evidence_receipt_step_count']} | "
            f"{row['execution_receipt_status']} | {row['blocker']} |"
        ),
    ]


def build_receipt_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Cascade Benchmark Evidence Receipt Coordination Receipt",
        "",
        "| execution_status | phase1_gate_status | manifest_coordination_status | blocker |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['execution_status']} | {row['phase1_gate_status']} | "
            f"{row['manifest_coordination_status']} | controlled_benchmark_timing_pending |"
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

    card_csv = tables_dir / "cascade_benchmark_evidence_receipt_coordination_card.csv"
    card_json = tables_dir / "cascade_benchmark_evidence_receipt_coordination_card.json"
    card_md = figures_dir / "cascade_benchmark_evidence_receipt_coordination_card.md"
    fill_csv = tables_dir / "cascade_benchmark_evidence_receipt_coordination_writeback.csv"
    fill_json = tables_dir / "cascade_benchmark_evidence_receipt_coordination_writeback.json"
    fill_md = figures_dir / "cascade_benchmark_evidence_receipt_coordination_writeback.md"
    receipt_json = tables_dir / "cascade_benchmark_evidence_receipt_coordination_receipt.json"
    receipt_md = figures_dir / "cascade_benchmark_evidence_receipt_coordination_receipt.md"

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
    wave8_receipt = load_json_dict("results/tables/wave8_exploration_baseline_closure_receipt.json")
    manifest_receipt = load_json_dict("results/tables/cascade_benchmark_manifest_coordination_receipt.json")
    lightoverlap_receipt = load_json_dict(
        "results/tables/speaker_profile_lightoverlap_diagnostic_coordination_receipt.json"
    )
    assert_writeback_preconditions(wave8_receipt, manifest_receipt, lightoverlap_receipt)

    receipt_path = PROJECT_ROOT / "results/tables/cascade_benchmark_evidence_receipt_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict("results/tables/cascade_benchmark_evidence_receipt_coordination_receipt.json")
        if str(existing.get("execution_status", "")) == "cascade_benchmark_evidence_receipt_coordination_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "cascade_benchmark_evidence_receipt_coordination_complete",
                "blocker": "controlled_benchmark_timing_pending",
            }

    card_rows = build_coordination_rows()
    evidence_step_count = count_evidence_receipt_steps()
    fill_row = build_fill_row(card_rows, evidence_step_count)
    receipt_row = build_receipt_row(wave8_receipt, manifest_receipt, evidence_step_count)
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "evidence_receipt_step_count": fill_row["evidence_receipt_step_count"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write cascade benchmark evidence receipt coordination after Wave8 manifest boundary."
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
