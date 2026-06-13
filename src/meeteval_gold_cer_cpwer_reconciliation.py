from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .io_helpers import to_float


RECONCILIATION_COLUMNS = [
    "case_id",
    "hypothesis_source",
    "gold_cer",
    "official_cpwer",
    "absolute_gap",
    "gap_direction",
    "reconciled",
    "tokenization_mode",
    "result_label",
    "observation",
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



def build_cer_lookup() -> dict[tuple[str, str], float]:
    lookup: dict[tuple[str, str], float] = {}
    for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "cer_results.csv"):
        case_id = str(row.get("case_id", ""))
        method = str(row.get("method", ""))
        cer = to_float(row.get("cer"))
        if case_id and method and cer is not None:
            lookup[(case_id, method)] = cer
    return lookup


def build_reconciliation_rows(
    meeteval_rows: list[dict[str, Any]],
    cer_lookup: dict[tuple[str, str], float],
    tolerance: float = 1e-4,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in meeteval_rows:
        case_id = str(entry.get("case_id", ""))
        hypothesis_source = str(entry.get("hypothesis_source", ""))
        cpwer = to_float(entry.get("official_cpwer"))
        cer = cer_lookup.get((case_id, hypothesis_source))
        if not case_id or cpwer is None or cer is None:
            continue
        gap = round(cpwer - cer, 6)
        reconciled = abs(gap) <= tolerance
        if reconciled:
            direction = "match"
            observation = "Character-level cpWER dry-run matches gold CER for the selected hypothesis route."
        elif gap > 0:
            direction = "cpwer_higher"
            observation = "cpWER exceeds gold CER; inspect tokenization or hypothesis route alignment."
        else:
            direction = "cpwer_lower"
            observation = "cpWER is below gold CER; inspect scoring normalization assumptions."
        rows.append(
            {
                "case_id": case_id,
                "hypothesis_source": hypothesis_source,
                "gold_cer": cer,
                "official_cpwer": cpwer,
                "absolute_gap": abs(gap),
                "gap_direction": direction,
                "reconciled": reconciled,
                "tokenization_mode": str(entry.get("tokenization_mode", "")),
                "result_label": "experimental/frontier",
                "observation": observation,
            }
        )
    return sorted(rows, key=lambda row: str(row["case_id"]))


def build_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not rows:
        return []
    reconciled_count = sum(1 for row in rows if row["reconciled"])
    return [
        {"metric": "gold_case_count", "value": str(len(rows)), "label": "stable/gold"},
        {
            "metric": "reconciled_case_count",
            "value": str(reconciled_count),
            "label": "experimental/frontier",
        },
        {
            "metric": "reconciliation_rate",
            "value": str(round(reconciled_count / len(rows), 4)),
            "label": "experimental/frontier",
        },
        {
            "metric": "max_absolute_gap",
            "value": str(max(float(row["absolute_gap"]) for row in rows)),
            "label": "experimental/frontier",
        },
    ]


def build_summary_lines(
    reconciliation_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, str]],
) -> list[str]:
    lines = [
        "# MeetEval Gold CER cpWER Reconciliation (experimental/frontier)",
        "",
        "Label: `experimental/frontier` — compares character-level MeetEval cpWER dry-runs",
        "against verified gold CER for the same hypothesis route. Does not overwrite gold tables.",
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
            "## Per-case Reconciliation",
            "",
            "| case_id | hypothesis_source | gold_cer | official_cpwer | absolute_gap | reconciled |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in reconciliation_rows:
        lines.append(
            f"| {row['case_id']} | {row['hypothesis_source']} | {row['gold_cer']} | "
            f"{row['official_cpwer']} | {row['absolute_gap']} | {row['reconciled']} |"
        )
    return lines


def build_reconciliation_report() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    meeteval_path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_character_level_official_execution.json"
    meeteval_rows = json.loads(meeteval_path.read_text(encoding="utf-8"))
    if not isinstance(meeteval_rows, list):
        meeteval_rows = []
    reconciliation_rows = build_reconciliation_rows(meeteval_rows, build_cer_lookup())
    return reconciliation_rows, build_summary_rows(reconciliation_rows)


def write_outputs(
    reconciliation_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    figure_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    csv_path = table_dir / "meeteval_gold_cer_cpwer_reconciliation.csv"
    json_path = table_dir / "meeteval_gold_cer_cpwer_reconciliation.json"
    summary_csv_path = table_dir / "meeteval_gold_cer_cpwer_reconciliation_summary.csv"
    summary_json_path = table_dir / "meeteval_gold_cer_cpwer_reconciliation_summary.json"
    md_path = figure_dir / "meeteval_gold_cer_cpwer_reconciliation.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=RECONCILIATION_COLUMNS)
        writer.writeheader()
        writer.writerows(reconciliation_rows)
    json_path.write_text(json.dumps(reconciliation_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    with summary_csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)
    summary_json_path.write_text(
        json.dumps(summary_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(
        "\n".join(build_summary_lines(reconciliation_rows, summary_rows)) + "\n",
        encoding="utf-8",
    )
    return csv_path, json_path, summary_csv_path, summary_json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconcile MeetEval character-level cpWER dry-runs with verified gold CER."
    )
    return parser.parse_args()


def main() -> None:
    _ = parse_args()
    _ = load_config()
    reconciliation_rows, summary_rows = build_reconciliation_report()
    paths = write_outputs(reconciliation_rows, summary_rows)
    for path in paths:
        print(f"Wrote: {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
