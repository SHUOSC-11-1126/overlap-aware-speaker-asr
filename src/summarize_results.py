from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config


SUMMARY_COLUMNS = [
    "case_id",
    "overlap_level",
    "mixed_cer",
    "separated_cer",
    "separated_cleaned_cer",
    "best_method",
    "observation",
]


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def build_summary() -> list[dict[str, Any]]:
    config = load_config()
    overlap_map = {case["id"]: case.get("overlap_level") for case in config.get("audio_cases", [])}

    cer_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "cer_results.csv")
    by_case: dict[str, dict[str, Any]] = {}
    for row in cer_rows:
        case_id = str(row.get("case_id", ""))
        by_case.setdefault(case_id, {})[str(row.get("method", ""))] = row

    comparison_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "mixed_vs_separated_comparison.csv")
    comparison_by_case = {str(row.get("case_id", "")): row for row in comparison_rows}

    benchmark_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "separated_asr_benchmark.csv")
    benchmark_by_case = {str(row.get("case_id", "")): row for row in benchmark_rows}

    cases = sorted(set(by_case.keys()) | set(comparison_by_case.keys()) | set(benchmark_by_case.keys()))
    summary_rows: list[dict[str, Any]] = []
    for case_id in cases:
        methods = by_case.get(case_id, {})
        mixed_cer = to_float(methods.get("mixed_whisper", {}).get("cer"))
        separated_cer = to_float(methods.get("separated_whisper", {}).get("cer"))
        cleaned_cer = to_float(methods.get("separated_whisper_cleaned", {}).get("cer"))

        available = [(name, value) for name, value in [
            ("mixed_whisper", mixed_cer),
            ("separated_whisper", separated_cer),
            ("separated_whisper_cleaned", cleaned_cer),
        ] if value is not None]
        best_method = min(available, key=lambda item: item[1])[0] if available else ""

        if case_id == "NoOverlap":
            observation = "Separated speaker-track ASR substantially reduced CER compared with mixed ASR."
        elif case_id == "LightOverlap":
            observation = (
                "Separated ASR performed worse than mixed ASR due to repeated hallucinated fragments; "
                "duplicate suppression reduced but did not fully solve the issue."
            )
        elif case_id:
            observation = "Benchmark case available for comparative analysis."
        else:
            observation = ""

        summary_rows.append(
            {
                "case_id": case_id,
                "overlap_level": overlap_map.get(case_id, ""),
                "mixed_cer": mixed_cer if mixed_cer is not None else "",
                "separated_cer": separated_cer if separated_cer is not None else "",
                "separated_cleaned_cer": cleaned_cer if cleaned_cer is not None else "",
                "best_method": best_method,
                "observation": observation,
            }
        )

    return summary_rows


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    fig_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    csv_path = table_dir / "current_results_summary.csv"
    json_path = table_dir / "current_results_summary.json"
    md_path = fig_dir / "current_results_summary.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Current Results Summary",
        "",
        "| case_id | overlap_level | mixed_cer | separated_cer | separated_cleaned_cer | best_method | observation |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        md_lines.append(
            "| {case_id} | {overlap_level} | {mixed_cer} | {separated_cer} | {separated_cleaned_cer} | {best_method} | {observation} |".format(
                **{k: str(v) for k, v in row.items()}
            )
        )
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return csv_path, json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize current CER results")
    return parser.parse_args()


def main() -> None:
    _ = parse_args()
    rows = build_summary()
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote summary CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote summary JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote summary MD: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
