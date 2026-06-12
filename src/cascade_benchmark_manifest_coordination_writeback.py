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
    "manifest_step_count",
    "execution_receipt_status",
    "blocker",
    "fill_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "coordination_scope",
    "wave7_closure_status",
    "benchmark_readiness_status",
    "manifest_step_count",
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


def count_manifest_steps() -> str:
    rows = load_json_rows("results/tables/cascade_benchmark_manifest_template.json")
    return str(len(rows)) if rows else "4"


def assert_writeback_preconditions(
    wave7_receipt: dict[str, Any],
    benchmark_receipt: dict[str, Any],
    speaker_scope_receipt: dict[str, Any],
) -> None:
    if str(wave7_receipt.get("execution_status", "")) != "wave7_exploration_baseline_closure_complete":
        raise RuntimeError("Wave7 closure must be complete before cascade benchmark manifest coordination")
    if str(benchmark_receipt.get("execution_status", "")) != "cascade_benchmark_coordination_writeback_complete":
        raise RuntimeError("Cascade benchmark readiness coordination must be complete before manifest coordination")
    if str(speaker_scope_receipt.get("execution_status", "")) != "speaker_profile_case_scope_coordination_complete":
        raise RuntimeError(
            "Speaker profile case-scope coordination must be complete before manifest coordination"
        )
    manifest_path = PROJECT_ROOT / "results/tables/cascade_benchmark_manifest_template.json"
    if not manifest_path.exists():
        raise RuntimeError("Missing prerequisite artifact: results/tables/cascade_benchmark_manifest_template.json")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "manifest_template_ready",
            "headline": "Benchmark manifest template lists controlled timing capture steps",
            "artifact_anchor": "results/tables/cascade_benchmark_manifest_template.csv",
            "coordination_note": "Template-only metadata fields (TODO); not a completed benchmark session.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "phase1_gold_gate",
            "headline": "phase1_gold_runtime_foundation awaits controlled hardware fill",
            "artifact_anchor": "results/tables/cascade_benchmark_evidence_receipt.json",
            "coordination_note": "Evidence receipt scaffold stays template-only until timing capture runs.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "readiness_link",
            "headline": "Wave6 benchmark readiness coordination defers timing claims to manifest boundary",
            "artifact_anchor": "results/figures/cascade_benchmark_readiness_coordination_card.md",
            "coordination_note": "repo_local_runtime_only — do not mix with stable gold CER tables.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave7_boundary",
            "headline": "Wave7 closure keeps manifest coordination separate from gold baseline",
            "artifact_anchor": "results/figures/wave7_exploration_baseline_closure_card.md",
            "coordination_note": "Coordination writeback only; no controlled benchmark session metadata recorded.",
            "result_label": "experimental/frontier",
        },
    ]


def build_fill_row(rows: list[dict[str, str]], manifest_step_count: str) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "cascade_benchmark_manifest_coordination_card",
        "coordination_section_count": str(len(rows)),
        "manifest_step_count": manifest_step_count,
        "execution_receipt_status": "cascade_benchmark_manifest_coordination_complete",
        "blocker": "controlled_benchmark_timing_pending",
        "fill_note": (
            "Filled cascade benchmark manifest coordination card after Wave7 speaker profile case-scope; "
            "manifest template remains unfilled for controlled timing."
        ),
    }


def build_receipt_row(
    wave7_receipt: dict[str, Any],
    benchmark_receipt: dict[str, Any],
    manifest_step_count: str,
) -> dict[str, str]:
    return {
        "execution_status": "cascade_benchmark_manifest_coordination_complete",
        "coordination_scope": "wave7_cascade_benchmark_manifest",
        "wave7_closure_status": str(wave7_receipt.get("execution_status", "")),
        "benchmark_readiness_status": str(benchmark_receipt.get("execution_status", "")),
        "manifest_step_count": manifest_step_count,
        "expected_inputs": (
            "Cascade benchmark manifest template, readiness coordination receipt, and Wave7 closure."
        ),
        "writeback_note": (
            "experimental/frontier coordination only; does not record controlled benchmark session metadata."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Cascade Benchmark Manifest Coordination Card (experimental/frontier)",
        "",
        "Manifest boundary coordination — not a controlled timing execution claim.",
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
        "# Cascade Benchmark Manifest Coordination Writeback",
        "",
        "| fill_status | manifest_step_count | execution_receipt_status | blocker |",
        "| --- | ---: | --- | --- |",
        (
            f"| {row['fill_status']} | {row['manifest_step_count']} | "
            f"{row['execution_receipt_status']} | {row['blocker']} |"
        ),
    ]


def build_receipt_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Cascade Benchmark Manifest Coordination Receipt",
        "",
        "| execution_status | manifest_step_count | benchmark_readiness_status | blocker |",
        "| --- | ---: | --- | --- |",
        (
            f"| {row['execution_status']} | {row['manifest_step_count']} | "
            f"{row['benchmark_readiness_status']} | controlled_benchmark_timing_pending |"
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

    card_csv = tables_dir / "cascade_benchmark_manifest_coordination_card.csv"
    card_json = tables_dir / "cascade_benchmark_manifest_coordination_card.json"
    card_md = figures_dir / "cascade_benchmark_manifest_coordination_card.md"
    fill_csv = tables_dir / "cascade_benchmark_manifest_coordination_writeback.csv"
    fill_json = tables_dir / "cascade_benchmark_manifest_coordination_writeback.json"
    fill_md = figures_dir / "cascade_benchmark_manifest_coordination_writeback.md"
    receipt_json = tables_dir / "cascade_benchmark_manifest_coordination_receipt.json"
    receipt_md = figures_dir / "cascade_benchmark_manifest_coordination_receipt.md"

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
    wave7_receipt = load_json_dict("results/tables/wave7_exploration_baseline_closure_receipt.json")
    benchmark_receipt = load_json_dict("results/tables/cascade_benchmark_readiness_coordination_receipt.json")
    speaker_scope_receipt = load_json_dict("results/tables/speaker_profile_case_scope_coordination_receipt.json")
    assert_writeback_preconditions(wave7_receipt, benchmark_receipt, speaker_scope_receipt)

    receipt_path = PROJECT_ROOT / "results/tables/cascade_benchmark_manifest_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict("results/tables/cascade_benchmark_manifest_coordination_receipt.json")
        if str(existing.get("execution_status", "")) == "cascade_benchmark_manifest_coordination_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "cascade_benchmark_manifest_coordination_complete",
                "blocker": "controlled_benchmark_timing_pending",
            }

    card_rows = build_coordination_rows()
    manifest_step_count = count_manifest_steps()
    fill_row = build_fill_row(card_rows, manifest_step_count)
    receipt_row = build_receipt_row(wave7_receipt, benchmark_receipt, manifest_step_count)
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "manifest_step_count": fill_row["manifest_step_count"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write cascade benchmark manifest coordination after Wave7 speaker profile case-scope."
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
