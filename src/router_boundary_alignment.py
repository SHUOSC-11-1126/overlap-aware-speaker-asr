from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .io_helpers import to_float
from .separation_phase_diagram import GOLD_CASE_TIER_ANCHOR, compute_delta_cer

ALIGNMENT_COLUMNS = [
    "case_id",
    "overlap_ratio_anchor",
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
    "router_matches_oracle",
    "router_aligns_with_phase",
    "router_regret_cer",
    "decision_rule",
]

SUMMARY_COLUMNS = [
    "metric",
    "value",
    "label",
]


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))



def prefers_separation_route(selected_method: str) -> bool:
    return selected_method in {"separated_whisper", "separated_whisper_cleaned"}


def pick_oracle_method(methods: dict[str, float]) -> tuple[str, float]:
    ranked = sorted(methods.items(), key=lambda item: item[1])
    return ranked[0][0], ranked[0][1]


def build_alignment_rows(
    cer_rows: list[dict[str, Any]],
    decision_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    cer_by_case: dict[str, dict[str, float]] = {}
    for row in cer_rows:
        case_id = str(row.get("case_id", ""))
        method = str(row.get("method", ""))
        cer = to_float(row.get("cer"))
        if case_id and method and cer is not None:
            cer_by_case.setdefault(case_id, {})[method] = cer

    decision_by_case = {str(row.get("case_id", "")): row for row in decision_rows}
    alignment_rows: list[dict[str, Any]] = []

    for case_id in sorted(cer_by_case.keys()):
        methods = cer_by_case[case_id]
        mixed = methods.get("mixed_whisper")
        separated = methods.get("separated_whisper")
        cleaned = methods.get("separated_whisper_cleaned")
        if mixed is None or separated is None:
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
        decision = decision_by_case.get(case_id, {})
        selected_method = str(decision.get("selected_method", ""))
        selected_cer = available.get(selected_method, oracle_cer)
        delta_sep = compute_delta_cer(mixed, separated)
        separation_helps = delta_sep < 0
        prefers_sep = prefers_separation_route(selected_method)
        _, anchor_ratio = GOLD_CASE_TIER_ANCHOR.get(case_id, ("", 0.0))

        alignment_rows.append(
            {
                "case_id": case_id,
                "overlap_ratio_anchor": anchor_ratio,
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
                "router_matches_oracle": selected_method == oracle_method,
                "router_aligns_with_phase": prefers_sep == separation_helps,
                "router_regret_cer": round(selected_cer - oracle_cer, 6),
                "decision_rule": str(decision.get("decision_rule", "")),
            }
        )
    return alignment_rows


def build_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not rows:
        return []
    count = len(rows)
    oracle_matches = sum(1 for row in rows if row["router_matches_oracle"])
    phase_aligned = sum(1 for row in rows if row["router_aligns_with_phase"])
    avg_regret = round(
        sum(float(row["router_regret_cer"]) for row in rows) / count,
        6,
    )
    return [
        {"metric": "gold_case_count", "value": str(count), "label": "stable/gold"},
        {
            "metric": "router_oracle_match_rate",
            "value": str(round(oracle_matches / count, 4)),
            "label": "experimental/frontier",
        },
        {
            "metric": "router_phase_alignment_rate",
            "value": str(round(phase_aligned / count, 4)),
            "label": "experimental/frontier",
        },
        {"metric": "average_router_regret_cer", "value": str(avg_regret), "label": "experimental/frontier"},
    ]


def build_summary_lines(
    alignment_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, str]],
) -> list[str]:
    lines = [
        "# Router Boundary Alignment (experimental/frontier)",
        "",
        "Label: `experimental/frontier` — compares feature router v2 gold decisions against",
        "the separation phase boundary without using CER as a routing input.",
        "",
        "## Summary",
        "",
        "| metric | value | label |",
        "| --- | ---: | --- |",
    ]
    for row in summary_rows:
        lines.append(f"| {row['metric']} | {row['value']} | {row['label']} |")

    lines.extend(
        [
            "",
            "## Per-case Alignment",
            "",
            "| case_id | selected | oracle | separation_helps | phase_aligned | regret_cer |",
            "| --- | --- | --- | --- | --- | ---: |",
        ]
    )
    for row in alignment_rows:
        lines.append(
            f"| {row['case_id']} | {row['selected_method']} | {row['oracle_method']} | "
            f"{row['separation_helps']} | {row['router_aligns_with_phase']} | {row['router_regret_cer']} |"
        )
    return lines


def build_alignment_report() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    cer_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "cer_results.csv")
    decision_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "routing_decisions_v2.csv")
    alignment_rows = build_alignment_rows(cer_rows, decision_rows)
    summary_rows = build_summary_rows(alignment_rows)
    return alignment_rows, summary_rows


def write_outputs(
    alignment_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    figure_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    csv_path = table_dir / "router_boundary_alignment.csv"
    json_path = table_dir / "router_boundary_alignment.json"
    summary_csv_path = table_dir / "router_boundary_alignment_summary.csv"
    summary_json_path = table_dir / "router_boundary_alignment_summary.json"
    md_path = figure_dir / "router_boundary_alignment.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=ALIGNMENT_COLUMNS)
        writer.writeheader()
        writer.writerows(alignment_rows)
    json_path.write_text(json.dumps(alignment_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    with summary_csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)
    summary_json_path.write_text(
        json.dumps(summary_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(
        "\n".join(build_summary_lines(alignment_rows, summary_rows)) + "\n",
        encoding="utf-8",
    )
    return csv_path, json_path, summary_csv_path, summary_json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit router v2 gold decisions against the separation phase boundary."
    )
    return parser.parse_args()


def main() -> None:
    _ = parse_args()
    _ = load_config()
    alignment_rows, summary_rows = build_alignment_report()
    paths = write_outputs(alignment_rows, summary_rows)
    for path in paths:
        print(f"Wrote: {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
