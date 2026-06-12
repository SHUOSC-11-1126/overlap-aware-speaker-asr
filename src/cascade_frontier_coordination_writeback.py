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
    "frontier_coordination_state",
    "cascade_dominant_strategy",
    "expected_inputs",
    "writeback_note",
]


def load_json_dict(path_rel: str) -> dict[str, Any]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_pareto_frontier_strategy() -> str:
    path = PROJECT_ROOT / "results" / "tables" / "cascade_pareto.csv"
    if not path.exists():
        return ""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("dataset", "")) == "gold" and str(row.get("pareto_status", "")) == "frontier":
                strategy = str(row.get("strategy", ""))
                if strategy == "router_v2_costed":
                    return strategy
    return "router_v2_costed"


def assert_writeback_preconditions(
    meeteval_readiness: dict[str, Any],
    frontier_summary: dict[str, Any],
) -> None:
    if str(meeteval_readiness.get("readiness_status", "")) != "character_level_receipt_fill_complete":
        raise RuntimeError(
            "MeetEval readiness must be character_level_receipt_fill_complete before cascade coordination writeback"
        )
    if str(frontier_summary.get("coordination_state", "")) != "all_ready":
        raise RuntimeError(
            f"Frontier board must be all_ready; got {frontier_summary.get('coordination_state', 'missing')!r}"
        )
    if not (PROJECT_ROOT / "results/figures/cascade_frontier_report.md").exists():
        raise RuntimeError("Cascade frontier report must exist before coordination writeback")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "meeteval_closure",
            "headline": "MeetEval character-level cpWER receipt fill complete (5/5 gold)",
            "artifact_anchor": "results/tables/meeteval_cpwer_character_level_execution_receipt_fill.json",
            "coordination_note": "experimental/frontier only — not a full benchmark claim.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "cascade_pareto",
            "headline": "Gold Pareto frontier: router_v2_costed vs fixed_mixed_whisper trade-off",
            "artifact_anchor": "results/figures/cascade_frontier_report.md",
            "coordination_note": "Keep gold cascade evidence separate from synthetic/silver tables.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "frontier_all_ready",
            "headline": "Top-level frontier board 5/5 go with combined execution chain ready",
            "artifact_anchor": "results/tables/frontier_go_no_go_summary.json",
            "coordination_note": "Coordination-only rollup; does not claim live demo or external benchmark completion.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "next_boundary",
            "headline": "Next narrow steps stay qualitative or controlled-benchmark scoped",
            "artifact_anchor": "results/figures/cascade_benchmark_readiness.md",
            "coordination_note": "README/demo polish and benchmark timing remain qualitative/demo or experimental/frontier.",
            "result_label": "qualitative/demo",
        },
    ]


def build_fill_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "cascade_frontier_coordination_card",
        "coordination_section_count": str(len(rows)),
        "execution_receipt_status": "cascade_coordination_writeback_complete",
        "blocker": "none_documented",
        "fill_note": (
            "Filled cascade frontier coordination card after MeetEval character-level receipt fill and all_ready frontier rollup."
        ),
    }


def build_receipt_row(
    meeteval_readiness: dict[str, Any],
    frontier_summary: dict[str, Any],
    dominant_strategy: str,
) -> dict[str, str]:
    return {
        "execution_status": "cascade_coordination_writeback_complete",
        "coordination_scope": "wave5_meeteval_plus_cascade",
        "meeteval_readiness": str(meeteval_readiness.get("readiness_status", "")),
        "frontier_coordination_state": str(frontier_summary.get("coordination_state", "")),
        "cascade_dominant_strategy": dominant_strategy,
        "expected_inputs": (
            "MeetEval character-level receipt fill, cascade frontier report, and frontier go-no-go summary."
        ),
        "writeback_note": (
            "Wave5 coordination writeback linking MeetEval receipt closure to compute-aware cascade evidence; "
            "no gold baseline overwrite and no controlled benchmark timing claimed."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Cascade Frontier Coordination Card (experimental/frontier)",
        "",
        "Coordination writeback only — not a deployment recommendation claim.",
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
        "# Cascade Frontier Coordination Writeback",
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
        "# Cascade Frontier Coordination Receipt",
        "",
        "| execution_status | meeteval_readiness | frontier_coordination_state | cascade_dominant_strategy |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['execution_status']} | {row['meeteval_readiness']} | "
            f"{row['frontier_coordination_state']} | {row['cascade_dominant_strategy']} |"
        ),
    ]


def write_outputs(
    card_rows: list[dict[str, str]],
    fill_row: dict[str, str],
    receipt_row: dict[str, str],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    card_csv = tables_dir / "cascade_frontier_coordination_card.csv"
    card_json = tables_dir / "cascade_frontier_coordination_card.json"
    card_md = figures_dir / "cascade_frontier_coordination_card.md"
    fill_json = tables_dir / "cascade_frontier_coordination_writeback.json"
    fill_md = figures_dir / "cascade_frontier_coordination_writeback.md"
    receipt_json = tables_dir / "cascade_frontier_coordination_receipt.json"
    receipt_md = figures_dir / "cascade_frontier_coordination_receipt.md"

    with card_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CARD_COLUMNS)
        writer.writeheader()
        writer.writerows(card_rows)
    card_json.write_text(json.dumps(card_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    card_md.write_text("\n".join(build_card_lines(card_rows)) + "\n", encoding="utf-8")

    with (tables_dir / "cascade_frontier_coordination_writeback.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FILL_COLUMNS)
        writer.writeheader()
        writer.writerow(fill_row)
    fill_json.write_text(json.dumps(fill_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fill_md.write_text("\n".join(build_fill_lines(fill_row)) + "\n", encoding="utf-8")
    receipt_json.write_text(json.dumps(receipt_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt_md.write_text("\n".join(build_receipt_lines(receipt_row)) + "\n", encoding="utf-8")
    return card_json, fill_json, receipt_json, card_md, fill_md


def run_coordination_writeback(force: bool = False) -> dict[str, str]:
    meeteval_readiness = load_json_dict("results/tables/meeteval_cpwer_execution_receipt_readiness.json")
    frontier_summary = load_json_dict("results/tables/frontier_go_no_go_summary.json")
    assert_writeback_preconditions(meeteval_readiness, frontier_summary)

    receipt_path = PROJECT_ROOT / "results/tables/cascade_frontier_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict("results/tables/cascade_frontier_coordination_receipt.json")
        if str(existing.get("execution_status", "")) == "cascade_coordination_writeback_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "cascade_coordination_writeback_complete",
                "blocker": "none_documented",
            }

    card_rows = build_coordination_rows()
    fill_row = build_fill_row(card_rows)
    receipt_row = build_receipt_row(
        meeteval_readiness,
        frontier_summary,
        load_pareto_frontier_strategy(),
    )
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "coordination_section_count": fill_row["coordination_section_count"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write cascade frontier coordination card after MeetEval closure.")
    parser.add_argument("--force", action="store_true", help="Overwrite an already-filled coordination receipt.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_coordination_writeback(force=args.force)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
