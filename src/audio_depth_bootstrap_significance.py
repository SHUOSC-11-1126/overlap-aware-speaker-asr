from __future__ import annotations

import argparse
from itertools import combinations

import numpy as np

from .audio_depth_router_common import draw_bar_chart, read_csv, rel, write_csv
from .audio_depth_systematic_common import BOOTSTRAP_CI_CSV, PAIRWISE_CSV, PREDICTIONS_CSV, SYSTEMATIC_FIGURE_PREFIX, safe_float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap AudioDepth systematic CER confidence intervals.")
    parser.add_argument("--n-boot", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_csv(PREDICTIONS_CSV)
    methods = [
        "old_router_v2",
        "previous_model_zoo_best",
        "hybrid_mlp_v2",
        "hybrid_late_fusion_v2",
        "calibrated_confidence_router",
        "cost_aware_router",
        "oracle_best",
    ]
    by_method = {m: [row for row in rows if row["model_name"] == m] for m in methods}
    n = min(len(v) for v in by_method.values() if v)
    rng = np.random.default_rng(args.seed)
    boot = {m: [] for m in methods if by_method.get(m)}
    for _ in range(args.n_boot):
        idx = rng.integers(0, n, size=n)
        for m, values in by_method.items():
            if not values:
                continue
            cers = np.asarray([safe_float(values[i]["predicted_cer"]) for i in idx], dtype=np.float32)
            boot[m].append(float(np.mean(cers)))
    ci_rows = []
    for m, values in boot.items():
        arr = np.asarray(values)
        ci_rows.append({"model_name": m, "mean_cer": round(float(arr.mean()), 6), "ci95_low": round(float(np.percentile(arr, 2.5)), 6), "ci95_high": round(float(np.percentile(arr, 97.5)), 6), "n_boot": args.n_boot, "sample_count": n})
    pair_rows = []
    for a, b in combinations(boot, 2):
        aa = np.asarray(boot[a])
        bb = np.asarray(boot[b])
        pair_rows.append({"method_a": a, "method_b": b, "p_a_better_than_b": round(float(np.mean(aa < bb)), 6), "mean_delta_a_minus_b": round(float(np.mean(aa - bb)), 6)})
    write_csv(BOOTSTRAP_CI_CSV, ci_rows)
    write_csv(PAIRWISE_CSV, pair_rows)
    draw_bar_chart(ci_rows, SYSTEMATIC_FIGURE_PREFIX / "audio_depth_systematic_bootstrap_ci.png", "model_name", "mean_cer", "Bootstrap mean CER")
    print(f"Wrote bootstrap CI to {rel(BOOTSTRAP_CI_CSV)}")


if __name__ == "__main__":
    main()
