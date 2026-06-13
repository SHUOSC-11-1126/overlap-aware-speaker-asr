from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .io_helpers import to_float
from .separation_phase_diagram import GOLD_CASE_TIER_ANCHOR, compute_delta_cer


BOUNDARY_COLUMNS = [
    "case_id",
    "overlap_ratio_anchor",
    "method",
    "cer",
    "dominant_error_type",
    "insertion_count",
    "repetition_count",
    "removed_count_if_cleaned",
    "delta_cer_separated",
    "separation_helps",
    "insertion_heavy",
    "explains_separation_harm",
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


def to_int(value: Any) -> int:
    try:
        return int(str(value).strip())
    except ValueError:
        return 0



def load_cer_by_case() -> dict[str, dict[str, float]]:
    grouped: dict[str, dict[str, float]] = {}
    for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "cer_results.csv"):
        case_id = str(row.get("case_id", ""))
        method = str(row.get("method", ""))
        cer = to_float(row.get("cer"))
        if case_id and method and cer is not None:
            grouped.setdefault(case_id, {})[method] = cer
    return grouped


def build_boundary_rows(
    error_rows: list[dict[str, Any]],
    cer_by_case: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    boundary_rows: list[dict[str, Any]] = []
    for row in error_rows:
        case_id = str(row.get("case_id", ""))
        method = str(row.get("method", ""))
        if method != "separated_whisper" or not case_id:
            continue

        methods = cer_by_case.get(case_id, {})
        mixed = methods.get("mixed_whisper")
        separated = methods.get("separated_whisper")
        if mixed is None or separated is None:
            continue

        _, anchor_ratio = GOLD_CASE_TIER_ANCHOR.get(case_id, ("", 0.0))
        insertion_count = to_int(row.get("insertion_count"))
        repetition_count = to_int(row.get("repetition_count"))
        substitution_count = to_int(row.get("substitution_count"))
        deletion_count = to_int(row.get("deletion_count"))
        total_errors = max(insertion_count + substitution_count + deletion_count, 1)
        insertion_share = insertion_count / total_errors
        delta_sep = compute_delta_cer(mixed, separated)
        separation_helps = delta_sep < 0
        insertion_heavy = str(row.get("dominant_error_type", "")) == "insertion" or insertion_share >= 0.5
        explains_harm = (not separation_helps) and insertion_heavy

        boundary_rows.append(
            {
                "case_id": case_id,
                "overlap_ratio_anchor": anchor_ratio,
                "method": method,
                "cer": separated,
                "dominant_error_type": str(row.get("dominant_error_type", "")),
                "insertion_count": insertion_count,
                "repetition_count": repetition_count,
                "removed_count_if_cleaned": to_int(row.get("removed_count_if_cleaned")),
                "delta_cer_separated": delta_sep,
                "separation_helps": separation_helps,
                "insertion_heavy": insertion_heavy,
                "explains_separation_harm": explains_harm,
            }
        )
    return sorted(boundary_rows, key=lambda item: float(item["overlap_ratio_anchor"]))


def build_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not rows:
        return []
    harmful = [row for row in rows if not row["separation_helps"]]
    helpful = [row for row in rows if row["separation_helps"]]
    harmful_explained = [row for row in harmful if row["explains_separation_harm"]]
    return [
        {"metric": "gold_case_count", "value": str(len(rows)), "label": "stable/gold"},
        {
            "metric": "separation_harmful_cases",
            "value": str(len(harmful)),
            "label": "experimental/frontier",
        },
        {
            "metric": "harmful_cases_insertion_explained",
            "value": str(len(harmful_explained)),
            "label": "experimental/frontier",
        },
        {
            "metric": "helpful_cases_avg_repetition",
            "value": str(
                round(
                    sum(int(row["repetition_count"]) for row in helpful) / max(len(helpful), 1),
                    2,
                )
            ),
            "label": "experimental/frontier",
        },
        {
            "metric": "harmful_cases_avg_repetition",
            "value": str(
                round(
                    sum(int(row["repetition_count"]) for row in harmful) / max(len(harmful), 1),
                    2,
                )
            ),
            "label": "experimental/frontier",
        },
    ]


def build_summary_lines(
    boundary_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, str]],
) -> list[str]:
    lines = [
        "# Error-Type Boundary Report (experimental/frontier)",
        "",
        "Label: `experimental/frontier` — links dominant separated ASR error modes to",
        "overlap regimes where separation helps or hurts. Does not modify gold references.",
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
            "## Separated Whisper by Overlap Regime",
            "",
            "| case_id | overlap_anchor | dominant_error | insertion | repetition | separation_helps | explains_harm |",
            "| --- | ---: | --- | ---: | ---: | --- | --- |",
        ]
    )
    for row in boundary_rows:
        lines.append(
            f"| {row['case_id']} | {row['overlap_ratio_anchor']} | {row['dominant_error_type']} | "
            f"{row['insertion_count']} | {row['repetition_count']} | {row['separation_helps']} | "
            f"{row['explains_separation_harm']} |"
        )
    return lines


def build_boundary_report() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    error_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "error_type_summary.csv")
    cer_by_case = load_cer_by_case()
    boundary_rows = build_boundary_rows(error_rows, cer_by_case)
    summary_rows = build_summary_rows(boundary_rows)
    return boundary_rows, summary_rows


def write_outputs(
    boundary_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    figure_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    csv_path = table_dir / "error_type_boundary_report.csv"
    json_path = table_dir / "error_type_boundary_report.json"
    summary_csv_path = table_dir / "error_type_boundary_report_summary.csv"
    summary_json_path = table_dir / "error_type_boundary_report_summary.json"
    md_path = figure_dir / "error_type_boundary_report.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=BOUNDARY_COLUMNS)
        writer.writeheader()
        writer.writerows(boundary_rows)
    json_path.write_text(json.dumps(boundary_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    with summary_csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)
    summary_json_path.write_text(
        json.dumps(summary_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(
        "\n".join(build_summary_lines(boundary_rows, summary_rows)) + "\n",
        encoding="utf-8",
    )
    return csv_path, json_path, summary_csv_path, summary_json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report how separated ASR error types explain the separation boundary."
    )
    return parser.parse_args()


def main() -> None:
    _ = parse_args()
    _ = load_config()
    boundary_rows, summary_rows = build_boundary_report()
    paths = write_outputs(boundary_rows, summary_rows)
    for path in paths:
        print(f"Wrote: {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
