from __future__ import annotations

from collections import defaultdict

from .audio_depth_router_common import PROJECT_ROOT, read_csv, rel, write_csv
from .audio_depth_systematic_common import safe_float
from .controlled_benchmark_common import CER_CSV, FIGURE_DIR, SENSITIVITY_CSV, draw_bar, draw_line


def avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def main() -> None:
    rows = read_csv(CER_CSV)
    summary = []
    all_row = {
        "group": "all",
        "sample_count": len(rows),
        "mixed_cer": avg([safe_float(r["mixed_cer"]) for r in rows]),
        "separated_cer": avg([safe_float(r["separated_cer"]) for r in rows]),
        "cleaned_cer": avg([safe_float(r["cleaned_cer"]) for r in rows]),
        "oracle_cer": avg([safe_float(r["oracle_cer"]) for r in rows]),
        "mean_route_gap": avg([safe_float(r["route_gap"]) for r in rows]),
        "mean_separation_gain": avg([safe_float(r["separation_gain"]) for r in rows]),
    }
    summary.append(all_row)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["overlap_ratio"])].append(row)
    ratio_rows = []
    for ratio, bucket in sorted(grouped.items(), key=lambda item: float(item[0])):
        ratio_rows.append(
            {
                "group": f"overlap_{ratio}",
                "overlap_ratio": ratio,
                "sample_count": len(bucket),
                "mixed_cer": avg([safe_float(r["mixed_cer"]) for r in bucket]),
                "separated_cer": avg([safe_float(r["separated_cer"]) for r in bucket]),
                "cleaned_cer": avg([safe_float(r["cleaned_cer"]) for r in bucket]),
                "oracle_cer": avg([safe_float(r["oracle_cer"]) for r in bucket]),
                "mean_route_gap": avg([safe_float(r["route_gap"]) for r in bucket]),
                "mean_separation_gain": avg([safe_float(r["separation_gain"]) for r in bucket]),
            }
        )
    summary.extend(ratio_rows)
    write_csv(SENSITIVITY_CSV, summary)
    draw_bar(rows, FIGURE_DIR / "controlled_route_gap_distribution.png", "sample_id", "route_gap", "Controlled route-gap distribution")
    draw_line(ratio_rows, FIGURE_DIR / "controlled_separation_gain_curve.png", "overlap_ratio", "mean_separation_gain", "Controlled separation gain by overlap")
    headroom = [
        {"method": "fixed_mixed", "cer": all_row["mixed_cer"]},
        {"method": "fixed_separated", "cer": all_row["separated_cer"]},
        {"method": "fixed_cleaned", "cer": all_row["cleaned_cer"]},
        {"method": "oracle", "cer": all_row["oracle_cer"]},
    ]
    draw_bar(headroom, FIGURE_DIR / "controlled_oracle_headroom.png", "method", "cer", "Controlled oracle headroom")
    helps = [r for r in ratio_rows if safe_float(r["mean_separation_gain"]) < 0]
    hurts = [r for r in ratio_rows if safe_float(r["mean_separation_gain"]) > 0]
    md = FIGURE_DIR / "controlled_route_sensitivity_summary.md"
    md.write_text(
        "\n".join(
            [
                "# Controlled Route Sensitivity Summary",
                "",
                f"- Samples: `{len(rows)}`",
                f"- Mean route gap: `{all_row['mean_route_gap']}`",
                f"- Oracle headroom over fixed mixed: `{round(all_row['mixed_cer'] - all_row['oracle_cer'], 6)}`",
                f"- Separation helps overlap ratios: `{', '.join(r['overlap_ratio'] for r in helps) or 'none'}`",
                f"- Separation hurts overlap ratios: `{', '.join(r['overlap_ratio'] for r in hurts) or 'none'}`",
                f"- Cleaned route average CER: `{all_row['cleaned_cer']}`",
                "",
                "The most useful routing-proof samples are those with larger route_gap and nonzero separation_gain magnitude.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote sensitivity summary to {rel(SENSITIVITY_CSV)}")


if __name__ == "__main__":
    main()
