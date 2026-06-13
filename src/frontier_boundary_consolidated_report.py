from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .io_helpers import read_json


SECTION_COLUMNS = [
    "section",
    "metric",
    "value",
    "label",
]

FINDING_COLUMNS = [
    "finding_id",
    "source_module",
    "statement",
    "label",
]


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def metric_map(rows: list[dict[str, Any]]) -> dict[str, str]:
    return {str(row.get("metric", "")): str(row.get("value", "")) for row in rows}


def build_section_rows() -> list[dict[str, str]]:
    trend_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "separation_phase_diagram_trend.csv")
    router_summary = metric_map(
        read_csv_rows(PROJECT_ROOT / "results" / "tables" / "router_boundary_alignment_summary.csv")
    )
    error_summary = metric_map(
        read_csv_rows(PROJECT_ROOT / "results" / "tables" / "error_type_boundary_report_summary.csv")
    )
    try:
        phase_points = read_json(PROJECT_ROOT / "results" / "tables" / "separation_phase_diagram.json")
    except FileNotFoundError:
        phase_points = []

    rows: list[dict[str, str]] = []
    rows.append(
        {
            "section": "separation_phase",
            "metric": "gold_point_count",
            "value": str(sum(1 for row in phase_points if row.get("source_label") == "stable/gold")),
            "label": "experimental/frontier",
        }
    )
    rows.append(
        {
            "section": "separation_phase",
            "metric": "silver_point_count",
            "value": str(sum(1 for row in phase_points if row.get("source_label") != "stable/gold")),
            "label": "experimental/frontier",
        }
    )
    for metric, value in router_summary.items():
        rows.append(
            {
                "section": "router_boundary",
                "metric": metric,
                "value": value,
                "label": "experimental/frontier",
            }
        )
    for metric, value in error_summary.items():
        rows.append(
            {
                "section": "error_type_boundary",
                "metric": metric,
                "value": value,
                "label": "experimental/frontier",
            }
        )
    rows.append(
        {
            "section": "separation_phase",
            "metric": "trend_bin_count",
            "value": str(len(trend_rows)),
            "label": "experimental/frontier",
        }
    )
    return rows


def build_finding_rows() -> list[dict[str, str]]:
    router_summary = metric_map(
        read_csv_rows(PROJECT_ROOT / "results" / "tables" / "router_boundary_alignment_summary.csv")
    )
    error_summary = metric_map(
        read_csv_rows(PROJECT_ROOT / "results" / "tables" / "error_type_boundary_report_summary.csv")
    )
    return [
        {
            "finding_id": "F1",
            "source_module": "separation_phase_diagram",
            "statement": "Separation benefit is regime-dependent; gold anchors show both helpful and harmful overlap bands.",
            "label": "experimental/frontier",
        },
        {
            "finding_id": "F2",
            "source_module": "router_boundary_alignment",
            "statement": (
                "Router v2 matches oracle and phase boundary on gold when "
                f"router_oracle_match_rate={router_summary.get('router_oracle_match_rate', 'n/a')}."
            ),
            "label": "experimental/frontier",
        },
        {
            "finding_id": "F3",
            "source_module": "error_type_boundary_report",
            "statement": (
                "Separation harm aligns with insertion-heavy separated errors when "
                f"harmful_cases_insertion_explained={error_summary.get('harmful_cases_insertion_explained', 'n/a')}."
            ),
            "label": "experimental/frontier",
        },
    ]


def build_summary_lines(section_rows: list[dict[str, str]], finding_rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Boundary Consolidated Report (experimental/frontier)",
        "",
        "Label: `experimental/frontier` — single entrypoint over the phase diagram, router alignment,",
        "and error-type boundary modules. Does not modify gold references.",
        "",
        "## Metrics",
        "",
        "| section | metric | value | label |",
        "| --- | --- | ---: | --- |",
    ]
    for row in section_rows:
        lines.append(f"| {row['section']} | {row['metric']} | {row['value']} | {row['label']} |")
    lines.extend(
        [
            "",
            "## Findings",
            "",
            "| finding_id | source_module | statement |",
            "| --- | --- | --- |",
        ]
    )
    for row in finding_rows:
        lines.append(f"| {row['finding_id']} | {row['source_module']} | {row['statement']} |")
    return lines


def build_consolidated_report() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    return build_section_rows(), build_finding_rows()


def write_outputs(
    section_rows: list[dict[str, str]],
    finding_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    figure_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    section_csv = table_dir / "frontier_boundary_consolidated_report.csv"
    section_json = table_dir / "frontier_boundary_consolidated_report.json"
    finding_csv = table_dir / "frontier_boundary_consolidated_findings.csv"
    finding_json = table_dir / "frontier_boundary_consolidated_findings.json"
    md_path = figure_dir / "frontier_boundary_consolidated_report.md"

    with section_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SECTION_COLUMNS)
        writer.writeheader()
        writer.writerows(section_rows)
    section_json.write_text(json.dumps(section_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    with finding_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FINDING_COLUMNS)
        writer.writeheader()
        writer.writerows(finding_rows)
    finding_json.write_text(json.dumps(finding_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_summary_lines(section_rows, finding_rows)) + "\n", encoding="utf-8")
    return section_csv, section_json, finding_csv, finding_json, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consolidate frontier boundary evidence from phase, router, and error-type modules."
    )
    return parser.parse_args()


def main() -> None:
    _ = parse_args()
    _ = load_config()
    section_rows, finding_rows = build_consolidated_report()
    paths = write_outputs(section_rows, finding_rows)
    for path in paths:
        print(f"Wrote: {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
