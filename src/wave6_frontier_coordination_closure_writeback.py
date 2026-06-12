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
    "meeteval_readiness",
    "demo_presentation_status",
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
    demo_wave5_fill: dict[str, Any],
    phase_receipt: dict[str, Any],
    cascade_receipt: dict[str, Any],
    meeteval_fill: dict[str, Any],
    frontier_summary: dict[str, Any],
) -> None:
    if str(demo_wave5_fill.get("fill_status", "")) != "writeback_filled":
        raise RuntimeError("Demo Wave5 presentation writeback must be filled before Wave6 closure")
    if str(phase_receipt.get("execution_status", "")) != "phase_coordination_writeback_complete":
        raise RuntimeError("Separation phase coordination must be complete before Wave6 closure")
    if str(cascade_receipt.get("execution_status", "")) != "cascade_coordination_writeback_complete":
        raise RuntimeError("Cascade coordination must be complete before Wave6 closure")
    if str(meeteval_fill.get("execution_receipt_status", "")) != "character_level_cpwer_receipt_fill_complete":
        raise RuntimeError("MeetEval character-level receipt fill must be complete before Wave6 closure")
    if str(frontier_summary.get("coordination_state", "")) != "all_ready":
        raise RuntimeError(
            f"Frontier board must be all_ready; got {frontier_summary.get('coordination_state', 'missing')!r}"
        )


def build_closure_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "meeteval_wave5",
            "headline": "MeetEval character-level cpWER receipt fill (5/5 gold)",
            "artifact_anchor": "results/tables/meeteval_cpwer_character_level_execution_receipt_fill.json",
            "coordination_note": "experimental/frontier; not a full benchmark claim.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "cascade_wave5",
            "headline": "Cascade Pareto coordination linked to MeetEval closure",
            "artifact_anchor": "results/figures/cascade_frontier_coordination_card.md",
            "coordination_note": "Gold router_v2_costed Pareto evidence; synthetic/silver kept separate.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "phase_wave5",
            "headline": "Separation phase boundary coordination (3/5 gold helps)",
            "artifact_anchor": "results/figures/separation_phase_coordination_card.md",
            "coordination_note": "Phase diagram + cascade boundary bridge; no deployment timing claim.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "demo_wave5",
            "headline": "Demo presentation Wave5 extension (6 polish sections)",
            "artifact_anchor": "results/tables/demo_wave5_presentation_writeback.json",
            "coordination_note": "qualitative/demo only; live delivery still blocked.",
            "result_label": "qualitative/demo",
        },
        {
            "section_id": "wave6_next_boundary",
            "headline": "Controlled cascade benchmark timing remains the next experimental frontier",
            "artifact_anchor": "results/figures/cascade_benchmark_readiness.md",
            "coordination_note": "Wave6 closure does not claim controlled hardware benchmark execution.",
            "result_label": "experimental/frontier",
        },
    ]


def build_fill_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "wave6_frontier_coordination_closure_card",
        "coordination_section_count": str(len(rows)),
        "execution_receipt_status": "wave6_coordination_closure_complete",
        "blocker": "none_documented",
        "fill_note": (
            "Wave6 frontier coordination closure rollup after Wave5 MeetEval, cascade, phase, and demo extensions."
        ),
    }


def build_receipt_row(
    meeteval_fill: dict[str, Any],
    demo_wave5_fill: dict[str, Any],
    frontier_summary: dict[str, Any],
) -> dict[str, str]:
    return {
        "execution_status": "wave6_coordination_closure_complete",
        "coordination_scope": "wave5_to_wave6_frontier_closure",
        "meeteval_readiness": str(meeteval_fill.get("execution_receipt_status", "")),
        "demo_presentation_status": str(demo_wave5_fill.get("storyboard_receipt_status", "")),
        "frontier_go_count": str(frontier_summary.get("go_count", "")),
        "expected_inputs": (
            "MeetEval, cascade, separation phase, and demo Wave5 coordination writebacks plus frontier go-no-go summary."
        ),
        "writeback_note": (
            "Wave6 coordination closure only; does not overwrite gold baseline or claim controlled benchmark timing."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Wave6 Frontier Coordination Closure Card",
        "",
        "Coordination closure rollup — not a benchmark or live-demo completion claim.",
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
        "# Wave6 Frontier Coordination Closure Writeback",
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
        "# Wave6 Frontier Coordination Closure Receipt",
        "",
        "| execution_status | meeteval_readiness | demo_presentation_status | frontier_go_count |",
        "| --- | --- | --- | ---: |",
        (
            f"| {row['execution_status']} | {row['meeteval_readiness']} | "
            f"{row['demo_presentation_status']} | {row['frontier_go_count']} |"
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

    card_csv = tables_dir / "wave6_frontier_coordination_closure_card.csv"
    card_json = tables_dir / "wave6_frontier_coordination_closure_card.json"
    card_md = figures_dir / "wave6_frontier_coordination_closure_card.md"
    fill_csv = tables_dir / "wave6_frontier_coordination_closure_writeback.csv"
    fill_json = tables_dir / "wave6_frontier_coordination_closure_writeback.json"
    fill_md = figures_dir / "wave6_frontier_coordination_closure_writeback.md"
    receipt_json = tables_dir / "wave6_frontier_coordination_closure_receipt.json"
    receipt_md = figures_dir / "wave6_frontier_coordination_closure_receipt.md"

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
    demo_wave5_fill = load_json_dict("results/tables/demo_wave5_presentation_writeback.json")
    phase_receipt = load_json_dict("results/tables/separation_phase_coordination_receipt.json")
    cascade_receipt = load_json_dict("results/tables/cascade_frontier_coordination_receipt.json")
    meeteval_fill = load_json_dict("results/tables/meeteval_cpwer_character_level_execution_receipt_fill.json")
    frontier_summary = load_json_dict("results/tables/frontier_go_no_go_summary.json")
    assert_closure_preconditions(
        demo_wave5_fill, phase_receipt, cascade_receipt, meeteval_fill, frontier_summary
    )

    receipt_path = PROJECT_ROOT / "results/tables/wave6_frontier_coordination_closure_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict("results/tables/wave6_frontier_coordination_closure_receipt.json")
        if str(existing.get("execution_status", "")) == "wave6_coordination_closure_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "wave6_coordination_closure_complete",
                "blocker": "none_documented",
            }

    card_rows = build_closure_rows()
    fill_row = build_fill_row(card_rows)
    receipt_row = build_receipt_row(meeteval_fill, demo_wave5_fill, frontier_summary)
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "coordination_section_count": fill_row["coordination_section_count"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write Wave6 frontier coordination closure after Wave5 chain.")
    parser.add_argument("--force", action="store_true", help="Overwrite an already-filled closure receipt.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_closure_writeback(force=args.force)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
