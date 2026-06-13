from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any

from .config import PROJECT_ROOT, load_config
from .io_helpers import to_float

POINT_COLUMNS = [
    "point_id",
    "source_label",
    "overlap_ratio",
    "overlap_ratio_kind",
    "tier",
    "mixed_cer",
    "separated_cer",
    "separated_cleaned_cer",
    "delta_cer_separated",
    "delta_cer_cleaned",
    "separation_helps",
]

TREND_COLUMNS = [
    "overlap_bin",
    "sample_count",
    "mean_delta_cer_separated",
    "median_delta_cer_separated",
    "separation_help_rate",
    "source_labels",
]

GOLD_CASE_TIER_ANCHOR = {
    "NoOverlap": ("SyntheticNoOverlap", 0.0),
    "LightOverlap": ("SyntheticLightOverlap", 0.15),
    "MidOverlap": ("SyntheticMidOverlap", 0.375),
    "HeavyOverlap": ("SyntheticHeavyOverlap", 0.60),
    "OppositeOverlap": ("SyntheticOppositeOverlap", 0.86),
}


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))



def overlap_bin_key(overlap_ratio: float, step: float = 0.05) -> float:
    return round(round(overlap_ratio / step) * step, 4)


def compute_delta_cer(mixed_cer: float, separated_cer: float) -> float:
    return round(separated_cer - mixed_cer, 6)


def build_gold_points(cer_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_case: dict[str, dict[str, float]] = defaultdict(dict)
    for row in cer_rows:
        case_id = str(row.get("case_id", ""))
        method = str(row.get("method", ""))
        cer = to_float(row.get("cer"))
        if case_id and method and cer is not None:
            by_case[case_id][method] = cer

    points: list[dict[str, Any]] = []
    for case_id in sorted(by_case.keys()):
        methods = by_case[case_id]
        mixed = methods.get("mixed_whisper")
        separated = methods.get("separated_whisper")
        cleaned = methods.get("separated_whisper_cleaned")
        if mixed is None or separated is None:
            continue
        tier, anchor_ratio = GOLD_CASE_TIER_ANCHOR.get(case_id, ("", 0.0))
        delta_sep = compute_delta_cer(mixed, separated)
        delta_cleaned = (
            compute_delta_cer(mixed, cleaned) if cleaned is not None else ""
        )
        points.append(
            {
                "point_id": case_id,
                "source_label": "stable/gold",
                "overlap_ratio": anchor_ratio,
                "overlap_ratio_kind": "tier_anchor",
                "tier": tier or case_id,
                "mixed_cer": mixed,
                "separated_cer": separated,
                "separated_cleaned_cer": cleaned if cleaned is not None else "",
                "delta_cer_separated": delta_sep,
                "delta_cer_cleaned": delta_cleaned,
                "separation_helps": delta_sep < 0,
            }
        )
    return points


def build_silver_points(
    cer_rows: list[dict[str, Any]],
    manifest_rows: list[dict[str, Any]],
    source_label: str,
) -> list[dict[str, Any]]:
    manifest_by_id = {str(row.get("sample_id", "")): row for row in manifest_rows}
    by_sample: dict[str, dict[str, float]] = defaultdict(dict)
    tier_by_sample: dict[str, str] = {}
    for row in cer_rows:
        sample_id = str(row.get("sample_id", ""))
        method = str(row.get("method", ""))
        cer = to_float(row.get("cer"))
        if sample_id and method and cer is not None:
            by_sample[sample_id][method] = cer
            tier_by_sample[sample_id] = str(row.get("tier", ""))

    points: list[dict[str, Any]] = []
    for sample_id in sorted(by_sample.keys()):
        methods = by_sample[sample_id]
        mixed = methods.get("mixed_whisper")
        separated = methods.get("separated_whisper")
        cleaned = methods.get("separated_whisper_cleaned")
        if mixed is None or separated is None:
            continue
        manifest = manifest_by_id.get(sample_id, {})
        overlap_ratio = to_float(manifest.get("overlap_ratio"))
        if overlap_ratio is None:
            continue
        delta_sep = compute_delta_cer(mixed, separated)
        delta_cleaned = (
            compute_delta_cer(mixed, cleaned) if cleaned is not None else ""
        )
        points.append(
            {
                "point_id": sample_id,
                "source_label": source_label,
                "overlap_ratio": overlap_ratio,
                "overlap_ratio_kind": "measured",
                "tier": tier_by_sample.get(sample_id, ""),
                "mixed_cer": mixed,
                "separated_cer": separated,
                "separated_cleaned_cer": cleaned if cleaned is not None else "",
                "delta_cer_separated": delta_sep,
                "delta_cer_cleaned": delta_cleaned,
                "separation_helps": delta_sep < 0,
            }
        )
    return points


def aggregate_trend_rows(points: list[dict[str, Any]], step: float = 0.05) -> list[dict[str, Any]]:
    grouped: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for point in points:
        overlap_ratio = to_float(point.get("overlap_ratio"))
        if overlap_ratio is None:
            continue
        grouped[overlap_bin_key(overlap_ratio, step)].append(point)

    trend_rows: list[dict[str, Any]] = []
    for overlap_bin in sorted(grouped.keys()):
        bucket = grouped[overlap_bin]
        deltas = [float(row["delta_cer_separated"]) for row in bucket]
        labels = sorted({str(row["source_label"]) for row in bucket})
        help_count = sum(1 for row in bucket if row.get("separation_helps"))
        trend_rows.append(
            {
                "overlap_bin": overlap_bin,
                "sample_count": len(bucket),
                "mean_delta_cer_separated": round(mean(deltas), 6),
                "median_delta_cer_separated": round(median(deltas), 6),
                "separation_help_rate": round(help_count / len(bucket), 4),
                "source_labels": ";".join(labels),
            }
        )
    return trend_rows


def build_phase_points(include_v2: bool = True) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    gold_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "cer_results.csv")
    silver_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_cer_results.csv")
    silver_manifest = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_manifest.csv")

    points = build_gold_points(gold_rows)
    points.extend(
        build_silver_points(silver_rows, silver_manifest, "synthetic/silver")
    )
    if include_v2:
        split_rows = read_csv_rows(
            PROJECT_ROOT / "results" / "tables" / "synthetic_split_cer_results.csv"
        )
        split_manifest = read_csv_rows(
            PROJECT_ROOT / "results" / "tables" / "synthetic_split_manifest.csv"
        )
        points.extend(
            build_silver_points(split_rows, split_manifest, "synthetic/silver_v2")
        )
    trend_rows = aggregate_trend_rows(points)
    return points, trend_rows


def build_summary_lines(points: list[dict[str, Any]], trend_rows: list[dict[str, Any]]) -> list[str]:
    gold_points = [row for row in points if row["source_label"] == "stable/gold"]
    silver_points = [row for row in points if row["source_label"] != "stable/gold"]
    harmful_gold = [row for row in gold_points if not row["separation_helps"]]
    helpful_gold = [row for row in gold_points if row["separation_helps"]]

    lines = [
        "# Separation Phase Diagram (experimental/frontier)",
        "",
        "Label: `experimental/frontier` — does not replace the stable gold benchmark.",
        "",
        "Delta CER is `CER(separated_whisper) - CER(mixed_whisper)`. Negative delta means separation helps.",
        "",
        "## Coverage",
        "",
        f"- Gold anchor points: {len(gold_points)}",
        f"- Silver measured points: {len(silver_points)}",
        f"- Trend bins: {len(trend_rows)}",
        "",
        "## Gold Boundary Anchors",
        "",
        "| case_id | overlap_ratio (tier anchor) | delta_cer_separated | separation_helps |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in gold_points:
        lines.append(
            f"| {row['point_id']} | {row['overlap_ratio']} | {row['delta_cer_separated']} | {row['separation_helps']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- Separation helps on {len(helpful_gold)}/{len(gold_points)} gold anchor cases.",
            f"- Separation hurts on {len(harmful_gold)}/{len(gold_points)} gold anchor cases"
            + (
                f" ({', '.join(row['point_id'] for row in harmful_gold)})."
                if harmful_gold
                else "."
            ),
            "- Silver sweep adds measured overlap-ratio points; treat as robustness evidence only.",
            "",
            "## Trend Bins",
            "",
            "| overlap_bin | sample_count | mean_delta_cer | separation_help_rate |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for row in trend_rows:
        lines.append(
            f"| {row['overlap_bin']} | {row['sample_count']} | {row['mean_delta_cer_separated']} | {row['separation_help_rate']} |"
        )
    return lines


def plot_phase_diagram(points: list[dict[str, Any]], trend_rows: list[dict[str, Any]], out_path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        from .compute_aware_cascade import write_fallback_png

        write_fallback_png(
            out_path,
            [
                {
                    "average_compute_cost": float(point["overlap_ratio"]),
                    "average_cer": float(point["delta_cer_separated"]),
                }
                for point in points
            ],
        )
        return

    color_map = {
        "stable/gold": "#d62728",
        "synthetic/silver": "#1f77b4",
        "synthetic/silver_v2": "#2ca02c",
    }

    fig, ax = plt.subplots(figsize=(10, 6))
    for source_label, color in color_map.items():
        subset = [row for row in points if row["source_label"] == source_label]
        if not subset:
            continue
        xs = [float(row["overlap_ratio"]) for row in subset]
        ys = [float(row["delta_cer_separated"]) for row in subset]
        marker = "D" if source_label == "stable/gold" else "o"
        size = 70 if source_label == "stable/gold" else 36
        ax.scatter(xs, ys, label=source_label, color=color, marker=marker, s=size, alpha=0.85)

    if trend_rows:
        ax.plot(
            [float(row["overlap_bin"]) for row in trend_rows],
            [float(row["mean_delta_cer_separated"]) for row in trend_rows],
            color="#444444",
            linestyle="--",
            linewidth=1.5,
            label="binned mean delta",
        )

    ax.axhline(0.0, color="#888888", linewidth=1.0, linestyle="-")
    ax.set_xlabel("Overlap ratio")
    ax.set_ylabel("Delta CER (separated - mixed)")
    ax.set_title("Separation Phase Diagram (experimental/frontier)")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def write_outputs(
    points: list[dict[str, Any]],
    trend_rows: list[dict[str, Any]],
) -> tuple[Path, Path, Path, Path, Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    figure_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    csv_path = table_dir / "separation_phase_diagram.csv"
    json_path = table_dir / "separation_phase_diagram.json"
    trend_csv_path = table_dir / "separation_phase_diagram_trend.csv"
    trend_json_path = table_dir / "separation_phase_diagram_trend.json"
    md_path = figure_dir / "separation_phase_diagram.md"
    png_path = figure_dir / "separation_phase_diagram.png"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=POINT_COLUMNS)
        writer.writeheader()
        writer.writerows(points)
    json_path.write_text(json.dumps(points, ensure_ascii=False, indent=2), encoding="utf-8")

    with trend_csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=TREND_COLUMNS)
        writer.writeheader()
        writer.writerows(trend_rows)
    trend_json_path.write_text(
        json.dumps(trend_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md_path.write_text("\n".join(build_summary_lines(points, trend_rows)) + "\n", encoding="utf-8")
    plot_phase_diagram(points, trend_rows, png_path)
    return csv_path, json_path, trend_csv_path, trend_json_path, md_path, png_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an experimental separation phase diagram from existing gold and silver CER tables."
    )
    parser.add_argument(
        "--no-v2",
        action="store_true",
        help="Exclude synthetic_overlap_v2 split CER points.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _ = load_config()
    points, trend_rows = build_phase_points(include_v2=not args.no_v2)
    paths = write_outputs(points, trend_rows)
    for path in paths:
        print(f"Wrote: {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
