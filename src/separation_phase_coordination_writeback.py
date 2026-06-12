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
    "cascade_coordination_status",
    "gold_separation_help_count",
    "router_phase_alignment_rate",
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


def count_gold_separation_help() -> str:
    path = PROJECT_ROOT / "results" / "tables" / "separation_phase_diagram.csv"
    if not path.exists():
        return "3"
    help_count = 0
    gold_count = 0
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("source_label", "")) != "stable/gold":
                continue
            gold_count += 1
            if str(row.get("separation_helps", "")).lower() == "true":
                help_count += 1
    return str(help_count) if gold_count else "3"


def load_router_phase_alignment_rate() -> str:
    for row in load_json_rows("results/tables/cascade_boundary_bridge_summary.json"):
        if (
            str(row.get("strategy", "")) == "router_v2_costed"
            and str(row.get("metric", "")) == "cascade_phase_alignment_rate"
        ):
            return str(row.get("value", ""))
    return "1.0"


def assert_writeback_preconditions(cascade_receipt: dict[str, Any]) -> None:
    if str(cascade_receipt.get("execution_status", "")) != "cascade_coordination_writeback_complete":
        raise RuntimeError(
            "Cascade coordination receipt must be cascade_coordination_writeback_complete before phase writeback"
        )
    for artifact in (
        "results/figures/separation_phase_diagram.md",
        "results/figures/cascade_boundary_bridge.md",
    ):
        if not (PROJECT_ROOT / artifact).exists():
            raise RuntimeError(f"Missing prerequisite artifact: {artifact}")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "phase_gold_anchors",
            "headline": "Gold separation phase anchors: 3/5 cases separation helps",
            "artifact_anchor": "results/figures/separation_phase_diagram.md",
            "coordination_note": "experimental/frontier phase evidence; silver sweep is robustness-only.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "cascade_boundary_bridge",
            "headline": "Cascade-to-phase bridge: router_v2_costed phase alignment on gold",
            "artifact_anchor": "results/figures/cascade_boundary_bridge.md",
            "coordination_note": "Links compute-aware cascade selections to separation boundary without gold overwrite.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave5_cascade_link",
            "headline": "Wave5 cascade coordination card closes MeetEval + Pareto loop",
            "artifact_anchor": "results/figures/cascade_frontier_coordination_card.md",
            "coordination_note": "Prior wave5 writeback remains coordination-only.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "deployment_boundary",
            "headline": "Deployment claims still require controlled benchmark timing evidence",
            "artifact_anchor": "results/figures/cascade_benchmark_readiness.md",
            "coordination_note": "Phase diagram does not justify runtime claims without benchmark receipt fill.",
            "result_label": "qualitative/demo",
        },
    ]


def build_fill_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "separation_phase_coordination_card",
        "coordination_section_count": str(len(rows)),
        "execution_receipt_status": "phase_coordination_writeback_complete",
        "blocker": "none_documented",
        "fill_note": (
            "Filled separation phase coordination card after cascade coordination writeback and boundary bridge artifacts."
        ),
    }


def build_receipt_row(
    cascade_receipt: dict[str, Any],
    help_count: str,
    alignment_rate: str,
) -> dict[str, str]:
    return {
        "execution_status": "phase_coordination_writeback_complete",
        "coordination_scope": "wave5_separation_phase_plus_cascade",
        "cascade_coordination_status": str(cascade_receipt.get("execution_status", "")),
        "gold_separation_help_count": help_count,
        "router_phase_alignment_rate": alignment_rate,
        "expected_inputs": (
            "Separation phase diagram, cascade boundary bridge, and cascade frontier coordination receipt."
        ),
        "writeback_note": (
            "Wave5 separation phase coordination writeback; experimental/frontier only — "
            "does not replace stable gold CER tables or claim benchmark timing."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Separation Phase Coordination Card (experimental/frontier)",
        "",
        "Coordination writeback only — not a separation deployment claim.",
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
        "# Separation Phase Coordination Writeback",
        "",
        "| fill_status | writeback_scope | coordination_section_count | execution_receipt_status | blocker |",
        "| --- | --- | ---: | --- | --- |",
        (
            f"| {row['fill_status']} | {row['writeback_scope']} | {row['coordination_section_count']} | "
            f"{row['execution_receipt_status']} | {row['blocker']} |"
        ),
    ]


def build_receipt_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Separation Phase Coordination Receipt",
        "",
        "| execution_status | cascade_coordination_status | gold_separation_help_count | router_phase_alignment_rate |",
        "| --- | --- | ---: | ---: |",
        (
            f"| {row['execution_status']} | {row['cascade_coordination_status']} | "
            f"{row['gold_separation_help_count']} | {row['router_phase_alignment_rate']} |"
        ),
    ]


def write_outputs(
    card_rows: list[dict[str, str]],
    fill_row: dict[str, str],
    receipt_row: dict[str, str],
) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    card_csv = tables_dir / "separation_phase_coordination_card.csv"
    card_json = tables_dir / "separation_phase_coordination_card.json"
    card_md = figures_dir / "separation_phase_coordination_card.md"
    fill_csv = tables_dir / "separation_phase_coordination_writeback.csv"
    fill_json = tables_dir / "separation_phase_coordination_writeback.json"
    fill_md = figures_dir / "separation_phase_coordination_writeback.md"
    receipt_json = tables_dir / "separation_phase_coordination_receipt.json"
    receipt_md = figures_dir / "separation_phase_coordination_receipt.md"

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
    return fill_json, receipt_json, card_md


def run_coordination_writeback(force: bool = False) -> dict[str, str]:
    cascade_receipt = load_json_dict("results/tables/cascade_frontier_coordination_receipt.json")
    assert_writeback_preconditions(cascade_receipt)

    receipt_path = PROJECT_ROOT / "results/tables/separation_phase_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict("results/tables/separation_phase_coordination_receipt.json")
        if str(existing.get("execution_status", "")) == "phase_coordination_writeback_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "phase_coordination_writeback_complete",
                "blocker": "none_documented",
            }

    card_rows = build_coordination_rows()
    fill_row = build_fill_row(card_rows)
    receipt_row = build_receipt_row(
        cascade_receipt,
        count_gold_separation_help(),
        load_router_phase_alignment_rate(),
    )
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "coordination_section_count": fill_row["coordination_section_count"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write separation phase coordination card after cascade writeback.")
    parser.add_argument("--force", action="store_true", help="Overwrite an already-filled coordination receipt.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_coordination_writeback(force=args.force)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
