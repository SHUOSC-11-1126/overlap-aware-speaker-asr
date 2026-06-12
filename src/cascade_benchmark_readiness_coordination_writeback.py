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
    "high_priority_artifact_count",
    "execution_receipt_status",
    "blocker",
    "fill_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "coordination_scope",
    "wave6_closure_status",
    "benchmark_status",
    "high_priority_artifact_count",
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


def count_high_priority_artifacts() -> str:
    rows = load_json_rows("results/tables/cascade_benchmark_readiness.json")
    count = sum(1 for row in rows if str(row.get("benchmark_priority", "")) == "high")
    return str(count) if count else "8"


def assert_writeback_preconditions(wave6_receipt: dict[str, Any]) -> None:
    if str(wave6_receipt.get("execution_status", "")) != "wave6_coordination_closure_complete":
        raise RuntimeError(
            "Wave6 closure receipt must be wave6_coordination_closure_complete before benchmark coordination"
        )
    for artifact in (
        "results/figures/cascade_benchmark_readiness.md",
        "results/figures/cascade_benchmark_evidence_receipt.md",
    ):
        if not (PROJECT_ROOT / artifact).exists():
            raise RuntimeError(f"Missing prerequisite artifact: {artifact}")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "readiness_high_priority",
            "headline": "Gold and synthetic_split runtime artifacts need controlled timing",
            "artifact_anchor": "results/figures/cascade_benchmark_readiness.md",
            "coordination_note": "repo_local_runtime_only — not controlled benchmark evidence.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "evidence_receipt_template",
            "headline": "Benchmark evidence receipt scaffold awaits controlled runtime fill",
            "artifact_anchor": "results/tables/cascade_benchmark_evidence_receipt.json",
            "coordination_note": "Template-only receipt; phase1_gold_runtime_foundation not executed.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave6_closure_link",
            "headline": "Wave6 frontier closure defers timing claims to this benchmark boundary",
            "artifact_anchor": "results/figures/wave6_frontier_coordination_closure_card.md",
            "coordination_note": "Closure card explicitly blocks controlled benchmark completion claims.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "deployment_boundary",
            "headline": "CER/compute trade-offs remain valid; runtime numbers stay provisional",
            "artifact_anchor": "results/figures/cascade_frontier_report.md",
            "coordination_note": "Do not mix provisional runtime with stable gold CER tables in README.",
            "result_label": "qualitative/demo",
        },
    ]


def build_fill_row(rows: list[dict[str, str]], high_priority_count: str) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "cascade_benchmark_readiness_coordination_card",
        "coordination_section_count": str(len(rows)),
        "high_priority_artifact_count": high_priority_count,
        "execution_receipt_status": "cascade_benchmark_coordination_writeback_complete",
        "blocker": "controlled_benchmark_timing_pending",
        "fill_note": (
            "Filled cascade benchmark readiness coordination card after Wave6 closure; "
            "controlled hardware timing not claimed."
        ),
    }


def build_receipt_row(wave6_receipt: dict[str, Any], high_priority_count: str) -> dict[str, str]:
    return {
        "execution_status": "cascade_benchmark_coordination_writeback_complete",
        "coordination_scope": "wave6_cascade_benchmark_boundary",
        "wave6_closure_status": str(wave6_receipt.get("execution_status", "")),
        "benchmark_status": "repo_local_runtime_only",
        "high_priority_artifact_count": high_priority_count,
        "expected_inputs": "Cascade benchmark readiness, evidence receipt scaffold, and Wave6 closure card.",
        "writeback_note": (
            "Coordination writeback only; does not record controlled benchmark session metadata or overwrite gold CER."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Cascade Benchmark Readiness Coordination Card (experimental/frontier)",
        "",
        "Benchmark boundary coordination — not a controlled timing execution claim.",
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
        "# Cascade Benchmark Readiness Coordination Writeback",
        "",
        "| fill_status | high_priority_artifact_count | execution_receipt_status | blocker |",
        "| --- | ---: | --- | --- |",
        (
            f"| {row['fill_status']} | {row['high_priority_artifact_count']} | "
            f"{row['execution_receipt_status']} | {row['blocker']} |"
        ),
    ]


def build_receipt_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Cascade Benchmark Readiness Coordination Receipt",
        "",
        "| execution_status | benchmark_status | high_priority_artifact_count | blocker |",
        "| --- | --- | ---: | --- |",
        (
            f"| {row['execution_status']} | {row['benchmark_status']} | "
            f"{row['high_priority_artifact_count']} | controlled_benchmark_timing_pending |"
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

    card_csv = tables_dir / "cascade_benchmark_readiness_coordination_card.csv"
    card_json = tables_dir / "cascade_benchmark_readiness_coordination_card.json"
    card_md = figures_dir / "cascade_benchmark_readiness_coordination_card.md"
    fill_csv = tables_dir / "cascade_benchmark_readiness_coordination_writeback.csv"
    fill_json = tables_dir / "cascade_benchmark_readiness_coordination_writeback.json"
    fill_md = figures_dir / "cascade_benchmark_readiness_coordination_writeback.md"
    receipt_json = tables_dir / "cascade_benchmark_readiness_coordination_receipt.json"
    receipt_md = figures_dir / "cascade_benchmark_readiness_coordination_receipt.md"

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
    wave6_receipt = load_json_dict("results/tables/wave6_frontier_coordination_closure_receipt.json")
    assert_writeback_preconditions(wave6_receipt)

    receipt_path = PROJECT_ROOT / "results/tables/cascade_benchmark_readiness_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict("results/tables/cascade_benchmark_readiness_coordination_receipt.json")
        if str(existing.get("execution_status", "")) == "cascade_benchmark_coordination_writeback_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "cascade_benchmark_coordination_writeback_complete",
                "blocker": "controlled_benchmark_timing_pending",
            }

    card_rows = build_coordination_rows()
    high_priority_count = count_high_priority_artifacts()
    fill_row = build_fill_row(card_rows, high_priority_count)
    receipt_row = build_receipt_row(wave6_receipt, high_priority_count)
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "coordination_section_count": fill_row["coordination_section_count"],
        "high_priority_artifact_count": fill_row["high_priority_artifact_count"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write cascade benchmark readiness coordination after Wave6 closure.")
    parser.add_argument("--force", action="store_true", help="Overwrite an already-filled coordination receipt.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_coordination_writeback(force=args.force)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
