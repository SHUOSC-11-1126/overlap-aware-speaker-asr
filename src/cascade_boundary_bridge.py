from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .compute_aware_cascade import load_decisions, load_gold_cases, select_strategy_method
from .config import PROJECT_ROOT, load_config
from .io_helpers import to_float
from .router_boundary_alignment import pick_oracle_method, prefers_separation_route
from .separation_phase_diagram import GOLD_CASE_TIER_ANCHOR, compute_delta_cer

CASCADE_STRATEGIES = ["budget_cascade", "router_v2_costed", "risk_aware_costed"]

BRIDGE_COLUMNS = [
    "strategy",
    "case_id",
    "overlap_ratio_anchor",
    "overlap_level",
    "risk_level",
    "selected_method",
    "oracle_method",
    "mixed_cer",
    "separated_cer",
    "separated_cleaned_cer",
    "selected_cer",
    "oracle_cer",
    "delta_cer_separated",
    "separation_helps",
    "prefers_separation_route",
    "cascade_matches_oracle",
    "cascade_aligns_with_phase",
    "cascade_regret_cer",
]

SUMMARY_COLUMNS = [
    "strategy",
    "metric",
    "value",
    "label",
]


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))



def build_cer_by_case() -> dict[str, dict[str, float]]:
    grouped: dict[str, dict[str, float]] = {}
    for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "cer_results.csv"):
        case_id = str(row.get("case_id", ""))
        method = str(row.get("method", ""))
        cer = to_float(row.get("cer"))
        if case_id and method and cer is not None:
            grouped.setdefault(case_id, {})[method] = cer
    return grouped


def build_bridge_rows(
    cases: list[dict[str, Any]],
    decisions: dict[str, dict[str, str]],
    cer_by_case: dict[str, dict[str, float]],
    strategies: list[str] | None = None,
) -> list[dict[str, Any]]:
    active_strategies = strategies or CASCADE_STRATEGIES
    bridge_rows: list[dict[str, Any]] = []

    for strategy in active_strategies:
        for case in cases:
            case_id = str(case.get("case_id", ""))
            methods = cer_by_case.get(case_id, {})
            mixed = methods.get("mixed_whisper")
            separated = methods.get("separated_whisper")
            cleaned = methods.get("separated_whisper_cleaned")
            if not case_id or mixed is None or separated is None:
                continue

            available = {
                name: value
                for name, value in [
                    ("mixed_whisper", mixed),
                    ("separated_whisper", separated),
                    ("separated_whisper_cleaned", cleaned),
                ]
                if value is not None
            }
            oracle_method, oracle_cer = pick_oracle_method(available)
            selected_method = select_strategy_method(strategy, case, decisions)
            if selected_method == "manual_review":
                continue
            selected_cer = available.get(selected_method, oracle_cer)
            delta_sep = compute_delta_cer(mixed, separated)
            separation_helps = delta_sep < 0
            prefers_sep = prefers_separation_route(selected_method)
            _, anchor_ratio = GOLD_CASE_TIER_ANCHOR.get(case_id, ("", 0.0))

            bridge_rows.append(
                {
                    "strategy": strategy,
                    "case_id": case_id,
                    "overlap_ratio_anchor": anchor_ratio,
                    "overlap_level": case.get("overlap_level", ""),
                    "risk_level": case.get("risk_level", ""),
                    "selected_method": selected_method,
                    "oracle_method": oracle_method,
                    "mixed_cer": mixed,
                    "separated_cer": separated,
                    "separated_cleaned_cer": cleaned if cleaned is not None else "",
                    "selected_cer": selected_cer,
                    "oracle_cer": oracle_cer,
                    "delta_cer_separated": delta_sep,
                    "separation_helps": separation_helps,
                    "prefers_separation_route": prefers_sep,
                    "cascade_matches_oracle": selected_method == oracle_method,
                    "cascade_aligns_with_phase": prefers_sep == separation_helps,
                    "cascade_regret_cer": round(selected_cer - oracle_cer, 6),
                }
            )

    return sorted(bridge_rows, key=lambda row: (str(row["strategy"]), str(row["case_id"])))


def build_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not rows:
        return []
    summary: list[dict[str, str]] = []
    strategies = sorted({str(row["strategy"]) for row in rows})
    for strategy in strategies:
        strategy_rows = [row for row in rows if str(row["strategy"]) == strategy]
        count = len(strategy_rows)
        oracle_matches = sum(1 for row in strategy_rows if row["cascade_matches_oracle"])
        phase_aligned = sum(1 for row in strategy_rows if row["cascade_aligns_with_phase"])
        avg_regret = round(sum(float(row["cascade_regret_cer"]) for row in strategy_rows) / count, 6)
        summary.extend(
            [
                {"strategy": strategy, "metric": "gold_case_count", "value": str(count), "label": "stable/gold"},
                {
                    "strategy": strategy,
                    "metric": "cascade_oracle_match_rate",
                    "value": str(round(oracle_matches / count, 4)),
                    "label": "experimental/frontier",
                },
                {
                    "strategy": strategy,
                    "metric": "cascade_phase_alignment_rate",
                    "value": str(round(phase_aligned / count, 4)),
                    "label": "experimental/frontier",
                },
                {
                    "strategy": strategy,
                    "metric": "average_cascade_regret_cer",
                    "value": str(avg_regret),
                    "label": "experimental/frontier",
                },
            ]
        )
    return summary


def build_summary_lines(
    bridge_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, str]],
) -> list[str]:
    lines = [
        "# Cascade Boundary Bridge (experimental/frontier)",
        "",
        "Label: `experimental/frontier` — bridges compute-aware cascade strategy",
        "selections to gold separation phase boundaries. Does not modify verified references.",
        "",
        "## Strategy Summary",
        "",
        "| strategy | metric | value | label |",
        "| --- | --- | ---: | --- |",
    ]
    for row in summary_rows:
        lines.append(f"| {row['strategy']} | {row['metric']} | {row['value']} | {row['label']} |")
    lines.extend(
        [
            "",
            "## Per-case Bridge",
            "",
            "| strategy | case_id | selected | oracle | phase_aligned | regret_cer |",
            "| --- | --- | --- | --- | --- | ---: |",
        ]
    )
    for row in bridge_rows:
        lines.append(
            f"| {row['strategy']} | {row['case_id']} | {row['selected_method']} | "
            f"{row['oracle_method']} | {row['cascade_aligns_with_phase']} | {row['cascade_regret_cer']} |"
        )
    return lines


def build_bridge_report() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    cases = load_gold_cases()
    decisions = load_decisions()
    bridge_rows = build_bridge_rows(cases, decisions, build_cer_by_case())
    return bridge_rows, build_summary_rows(bridge_rows)


def write_outputs(
    bridge_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    figure_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    csv_path = table_dir / "cascade_boundary_bridge.csv"
    json_path = table_dir / "cascade_boundary_bridge.json"
    summary_csv_path = table_dir / "cascade_boundary_bridge_summary.csv"
    summary_json_path = table_dir / "cascade_boundary_bridge_summary.json"
    md_path = figure_dir / "cascade_boundary_bridge.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=BRIDGE_COLUMNS)
        writer.writeheader()
        writer.writerows(bridge_rows)
    json_path.write_text(json.dumps(bridge_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    with summary_csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)
    summary_json_path.write_text(
        json.dumps(summary_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text("\n".join(build_summary_lines(bridge_rows, summary_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, summary_csv_path, summary_json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bridge compute-aware cascade strategies to separation phase boundaries on gold."
    )
    return parser.parse_args()


def main() -> None:
    _ = parse_args()
    _ = load_config()
    bridge_rows, summary_rows = build_bridge_report()
    paths = write_outputs(bridge_rows, summary_rows)
    for path in paths:
        print(f"Wrote: {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
