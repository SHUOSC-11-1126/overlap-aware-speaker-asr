from __future__ import annotations

from collections import defaultdict

import numpy as np

from .audio_depth_router_common import read_csv, rel, write_csv
from .audio_depth_systematic_common import safe_float
from .audiodepth_centric_common import (
    FEATURE_CORR_CSV,
    FEATURE_SUMMARY_CSV,
    FIGURE_DIR,
    METADATA_CSV,
    draw_bar,
    labelled_metadata,
    write_summary,
)


FEATURES = [
    "overlap_proxy_mean",
    "overlap_proxy_max",
    "overlap_proxy_std",
    "uncertainty_proxy_mean",
    "uncertainty_proxy_max",
    "uncertainty_proxy_std",
    "overlap_uncertainty_product",
]


def corr(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 3 or len(set(ys)) <= 1:
        return 0.0
    x = np.asarray(xs, dtype=np.float32)
    y = np.asarray(ys, dtype=np.float32)
    if float(np.std(x)) == 0.0 or float(np.std(y)) == 0.0:
        return 0.0
    return round(float(np.corrcoef(x, y)[0, 1]), 6)


def summarize_group(rows: list[dict[str, str]], key: str) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row.get(key, "unknown")].append(row)
    out = []
    for group, bucket in sorted(grouped.items()):
        item = {"group_key": key, "group": group, "sample_count": len(bucket)}
        for feature in FEATURES:
            vals = [safe_float(row.get(feature)) for row in bucket]
            item[f"{feature}_mean"] = round(float(np.mean(vals)), 6) if vals else 0.0
            item[f"{feature}_std"] = round(float(np.std(vals)), 6) if vals else 0.0
        out.append(item)
    return out


def main() -> None:
    rows = labelled_metadata()
    if not rows:
        raise SystemExit("No labelled AudioDepth v2 metadata found. Run build_deployable_audiodepth_v2 first.")
    summary = summarize_group(rows, "intended_family") + summarize_group(rows, "oracle_route")
    write_csv(FEATURE_SUMMARY_CSV, summary)
    route_codes = {"mixed": 0.0, "separated": 1.0, "cleaned": 2.0}
    route_targets = [route_codes.get(row.get("oracle_route", ""), 0.0) for row in rows]
    route_gap = [safe_float(row.get("route_gap")) for row in rows]
    sep_helpful = [1.0 if row.get("oracle_route") == "separated" else 0.0 for row in rows]
    corr_rows = []
    for feature in FEATURES:
        xs = [safe_float(row.get(feature)) for row in rows]
        corr_rows.extend(
            [
                {"feature": feature, "target": "oracle_route_code", "pearson_r": corr(xs, route_targets), "sample_count": len(rows)},
                {"feature": feature, "target": "route_gap", "pearson_r": corr(xs, route_gap), "sample_count": len(rows)},
                {"feature": feature, "target": "separation_helpful", "pearson_r": corr(xs, sep_helpful), "sample_count": len(rows)},
            ]
        )
    write_csv(FEATURE_CORR_CSV, corr_rows)
    family_rows = [row for row in summary if row["group_key"] == "intended_family"]
    draw_bar(family_rows, FIGURE_DIR / "audiodepth_v2_channel_statistics.png", "group", "overlap_proxy_mean_mean", "AudioDepth v2 overlap proxy by family")
    draw_bar([row for row in corr_rows if row["target"] == "separation_helpful"], FIGURE_DIR / "audiodepth_v2_route_correlation.png", "feature", "pearson_r", "Feature correlation with separation helpful")
    best = sorted(corr_rows, key=lambda row: abs(safe_float(row["pearson_r"])), reverse=True)[:5]
    mixed = [row for row in rows if row.get("oracle_route") == "mixed"]
    sep = [row for row in rows if row.get("oracle_route") == "separated"]
    sep_gap = abs(np.mean([safe_float(row["overlap_proxy_mean"]) for row in sep]) - np.mean([safe_float(row["overlap_proxy_mean"]) for row in mixed])) if mixed and sep else 0.0
    conclusion = "Current deployable proxies show usable but modest route signal." if sep_gap >= 0.01 else "Current deployable proxies are weak and need learned overlap detection."
    write_summary(
        FIGURE_DIR / "audiodepth_v2_feature_audit.md",
        "AudioDepth v2 Feature Audit",
        [
            f"- labelled samples: `{len(rows)}`",
            f"- mixed-vs-separated overlap proxy mean gap: `{sep_gap:.6f}`",
            f"- conclusion: {conclusion}",
            "",
            "Top correlations:",
            *[f"- `{row['feature']}` vs `{row['target']}`: `{row['pearson_r']}`" for row in best],
            "",
            "Cleaned route note: the current labelled controlled_v2 slice has no cleaned oracle winner, so cleaned-specific signature cannot be proven yet.",
        ],
    )
    print(f"Wrote AudioDepth v2 feature audit to {rel(FEATURE_SUMMARY_CSV)}")


if __name__ == "__main__":
    main()
