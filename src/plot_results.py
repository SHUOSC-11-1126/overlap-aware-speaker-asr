from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config


METHOD_ORDER = ["mixed_whisper", "separated_whisper", "separated_whisper_cleaned"]
METHOD_LABELS = {
    "mixed_whisper": "Mixed",
    "separated_whisper": "Separated",
    "separated_whisper_cleaned": "Separated + Cleaned",
}


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing results table: {path.relative_to(PROJECT_ROOT)}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def to_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(str(value).strip())
    except ValueError:
        return 0.0


def grouped_cer_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    grouped: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        case_id = str(row.get("case_id", ""))
        method = str(row.get("method", ""))
        if not case_id or not method:
            continue
        grouped[case_id][method] = to_float(row.get("cer"))
    return grouped


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def plot_cer_by_case(grouped: dict[str, dict[str, float]], out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cases = sorted(grouped.keys(), key=lambda x: x)
    x = range(len(cases))
    width = 0.25

    fig, ax = plt.subplots(figsize=(11, 6))
    for idx, method in enumerate(METHOD_ORDER):
        values = [grouped[case].get(method, 0.0) for case in cases]
        ax.bar([i + (idx - 1) * width for i in x], values, width=width, label=METHOD_LABELS[method])

    ax.set_xticks(list(x))
    ax.set_xticklabels(cases, rotation=20, ha="right")
    ax.set_ylabel("CER")
    ax.set_title("CER by Case and Method")
    ax.set_ylim(0, max(max(vals.values()) for vals in grouped.values()) * 1.15)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def plot_cer_by_method_average(grouped: dict[str, dict[str, float]], out_path: Path) -> dict[str, float]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    averages: dict[str, float] = {}
    for method in METHOD_ORDER:
        values = [methods[method] for methods in grouped.values() if method in methods]
        averages[method] = sum(values) / len(values) if values else 0.0

    fig, ax = plt.subplots(figsize=(8, 5))
    labels = [METHOD_LABELS[m] for m in METHOD_ORDER]
    values = [averages[m] for m in METHOD_ORDER]
    ax.bar(labels, values, color=["#4c78a8", "#f58518", "#54a24b"])
    ax.set_ylabel("Average CER")
    ax.set_title("Average CER by Method")
    ax.set_ylim(0, max(values) * 1.2 if values else 1.0)
    for idx, value in enumerate(values):
        ax.text(idx, value + max(values) * 0.03, f"{value:.3f}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return averages


def build_adaptive_rows(grouped: dict[str, dict[str, float]], config: dict[str, Any]) -> list[dict[str, Any]]:
    overlap_map = {case["id"]: case.get("overlap_level") for case in config.get("audio_cases", [])}
    rows: list[dict[str, Any]] = []
    for case_id in sorted(grouped.keys()):
        methods = grouped[case_id]
        available = [(method, cer) for method, cer in methods.items() if method in METHOD_ORDER]
        if not available:
            continue
        best_method, best_cer = min(available, key=lambda item: item[1])
        rows.append(
            {
                "case_id": case_id,
                "overlap_level": overlap_map.get(case_id, ""),
                "mixed_cer": methods.get("mixed_whisper", ""),
                "separated_cer": methods.get("separated_whisper", ""),
                "separated_cleaned_cer": methods.get("separated_whisper_cleaned", ""),
                "best_method": best_method,
                "best_cer": best_cer,
                "observation": (
                    "Oracle routing selects the lowest-CER method for this case."
                ),
            }
        )
    return rows


def write_table_outputs(rows: list[dict[str, Any]], averages: dict[str, float]) -> tuple[Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    ensure_dir(table_dir)
    csv_path = table_dir / "adaptive_routing_results.csv"
    json_path = table_dir / "adaptive_routing_results.json"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        fieldnames = [
            "case_id",
            "overlap_level",
            "mixed_cer",
            "separated_cer",
            "separated_cleaned_cer",
            "best_method",
            "best_cer",
            "observation",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "rows": rows,
        "average_cer": {
            "mixed_average": averages.get("mixed_whisper", 0.0),
            "separated_average": averages.get("separated_whisper", 0.0),
            "cleaned_average": averages.get("separated_whisper_cleaned", 0.0),
            "adaptive_best_average": sum(to_float(r["best_cer"]) for r in rows) / len(rows) if rows else 0.0,
        },
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_path, json_path


def update_summary_md(averages: dict[str, float], adaptive_best_average: float) -> Path:
    md_path = PROJECT_ROOT / "results" / "figures" / "current_results_summary.md"
    adaptive_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "adaptive_routing_results.csv")
    lines = [
        "# Current Results Summary",
        "",
        "## Core Findings",
        "",
        "- Separated speaker-track ASR is the best method on NoOverlap, HeavyOverlap, and OppositeOverlap.",
        "- Mixed ASR remains the best method on LightOverlap and MidOverlap.",
        "- Duplicate suppression improves the separated transcript on LightOverlap and MidOverlap, but does not overtake mixed ASR there.",
        "- Oracle routing across the verified cases gives the lowest average CER among the three fixed pipelines.",
        "",
        "## Average CER",
        "",
        f"- Mixed average: {averages.get('mixed_whisper', 0.0):.6f}",
        f"- Separated average: {averages.get('separated_whisper', 0.0):.6f}",
        f"- Cleaned average: {averages.get('separated_whisper_cleaned', 0.0):.6f}",
        f"- Adaptive best average: {adaptive_best_average:.6f}",
        "",
        "## Best Method By Case",
        "",
        "| case_id | best_method | best_cer |",
        "| --- | --- | ---: |",
    ]
    for row in adaptive_rows:
        lines.append(f"| {row['case_id']} | {row['best_method']} | {float(row['best_cer']):.6f} |")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot CER results and compute adaptive routing.")
    return parser.parse_args()


def main() -> None:
    _ = parse_args()
    config = load_config()
    rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "cer_results.csv")
    grouped = grouped_cer_rows(rows)
    fig_dir = PROJECT_ROOT / "results" / "figures"
    ensure_dir(fig_dir)

    cer_by_case_path = fig_dir / "cer_by_case.png"
    cer_by_method_path = fig_dir / "cer_by_method_average.png"
    best_method_md = PROJECT_ROOT / "results" / "figures" / "best_method_by_case.md"

    plot_cer_by_case(grouped, cer_by_case_path)
    averages = plot_cer_by_method_average(grouped, cer_by_method_path)
    adaptive_rows = build_adaptive_rows(grouped, config)
    csv_path, json_path = write_table_outputs(adaptive_rows, averages)

    best_method_lines = [
        "# Best Method by Case",
        "",
        "| case_id | best_method | best_cer |",
        "| --- | --- | ---: |",
    ]
    for row in adaptive_rows:
        best_method_lines.append(f"| {row['case_id']} | {row['best_method']} | {float(row['best_cer']):.6f} |")
    best_method_md.write_text("\n".join(best_method_lines), encoding="utf-8")

    update_summary_md(averages, sum(to_float(r["best_cer"]) for r in adaptive_rows) / len(adaptive_rows))

    print(f"Wrote figure: {cer_by_case_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote figure: {cer_by_method_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote markdown: {best_method_md.relative_to(PROJECT_ROOT)}")
    print(f"Wrote adaptive routing CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote adaptive routing JSON: {json_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
