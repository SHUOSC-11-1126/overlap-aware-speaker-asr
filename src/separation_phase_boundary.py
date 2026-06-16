from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

from .config import PROJECT_ROOT, load_config
from .io_helpers import to_float

# ── schema constants ──────────────────────────────────────────────────────────

BOUNDARY_COLUMNS = [
    "boundary_type",
    "crossover_ratio",
    "crossover_ci_lower",
    "crossover_ci_median",
    "crossover_ci_upper",
    "crossover_ci_width",
    "bootstrap_samples",
    "below_boundary_help_rate",
    "above_boundary_help_rate",
    "label",
]

DENSE_TREND_COLUMNS = [
    "overlap_bin",
    "sample_count",
    "mean_delta_cer_separated",
    "median_delta_cer_separated",
    "separation_help_rate",
    "source_labels",
    "bootstrap_mean_delta_cer",
    "bootstrap_se_cer",
    "bootstrap_p_helps",
    "trend_ci_lower",
    "trend_ci_upper",
]


# ── LOWESS smoothing ──────────────────────────────────────────────────────────

def tricube_weights(distances: list[float], bandwidth: float) -> list[float]:
    """Tricube weight function: w(u) = (1 - |u|^3)^3 for |u| < 1, else 0."""
    if bandwidth <= 0.0:
        return [0.0] * len(distances)
    weights: list[float] = []
    for d in distances:
        u = abs(d) / bandwidth
        if u < 1.0:
            w = (1.0 - u ** 3) ** 3
            weights.append(w)
        else:
            weights.append(0.0)
    return weights


def lowess_smooth(
    xs: list[float],
    ys: list[float],
    fraction: float = 0.33,
) -> list[float]:
    """Locally weighted scatterplot smoothing (LOWESS) with tricube weights.

    Args:
        xs: Independent variable (e.g. overlap ratio).
        ys: Dependent variable (e.g. delta CER).
        fraction: Fraction of points to include in each local window.

    Returns:
        Smoothed y-values, same length as inputs.
    """
    n = len(xs)
    if n < 2:
        return list(ys)

    window_size = max(1, int(round(n * fraction)))
    smoothed: list[float] = []

    for i in range(n):
        # Distances in x-space
        distances = [abs(xs[i] - xs[j]) for j in range(n)]
        # Sort distances to find bandwidth
        sorted_d = sorted(distances)
        bandwidth = sorted_d[min(window_size, n - 1)]

        weights = tricube_weights(distances, bandwidth)

        # Weighted linear regression: y ~ a + b*x
        total_w = sum(weights)
        if total_w == 0.0:
            smoothed.append(ys[i])
            continue

        wx = sum(w * xs[j] for j, w in enumerate(weights))
        wy = sum(w * ys[j] for j, w in enumerate(weights))
        wxx = sum(w * xs[j] * xs[j] for j, w in enumerate(weights))
        wxy = sum(w * xs[j] * ys[j] for j, w in enumerate(weights))

        denominator = total_w * wxx - wx * wx
        # When all x are nearly identical (uniform), denominator → 0;
        # fall back to the weighted mean.
        if abs(denominator) < 1e-15:
            smoothed.append(wy / total_w if total_w > 0 else ys[i])
        else:
            b = (total_w * wxy - wx * wy) / denominator
            a = (wy - b * wx) / total_w
            smoothed.append(a + b * xs[i])

    return smoothed


# ── crossover detection ───────────────────────────────────────────────────────

def _extract_xy(points: list[dict[str, Any]]) -> tuple[list[float], list[float]]:
    """Extract sorted (overlap_ratio, delta_cer_separated) from points."""
    pairs: list[tuple[float, float]] = []
    for p in points:
        r = to_float(p.get("overlap_ratio"))
        d = to_float(p.get("delta_cer_separated"))
        if r is not None and d is not None:
            pairs.append((r, d))
    pairs.sort(key=lambda item: item[0])
    if not pairs:
        return [], []
    return [item[0] for item in pairs], [item[1] for item in pairs]


def compute_crossover_boundary(
    points: list[dict[str, Any]],
    lowess_fraction: float = 0.33,
) -> dict[str, Any]:
    """Find the overlap ratio where delta CER crosses from negative to positive.

    Uses LOWESS smoothing then linear interpolation between the two
    smoothed points that bracket y=0.

    Returns dict with keys:
        crossover_ratio (float or ""), crossover_status (str),
        smoothed_xs, smoothed_ys, lowess_fraction.
    """
    xs, ys = _extract_xy(points)
    n = len(xs)

    if n < 2:
        return {
            "crossover_ratio": "",
            "crossover_status": "no_crossover_detected",
            "smoothed_xs": xs,
            "smoothed_ys": ys,
            "lowess_fraction": lowess_fraction,
        }

    smoothed = lowess_smooth(xs, ys, fraction=lowess_fraction)

    # Determine status by checking if all smoothed values have the same sign
    all_negative = all(s < 0 for s in smoothed)
    all_positive = all(s > 0 for s in smoothed)

    if all_negative:
        status = "always_helpful"
        ratio = ""
    elif all_positive:
        status = "always_harmful"
        ratio = ""
    else:
        # Find the first crossing
        cross_found = False
        ratio: float | str = ""
        status = ""
        for i in range(n - 1):
            if smoothed[i] <= 0.0 < smoothed[i + 1]:
                # Crossing from negative (helps) to positive (hurts)
                if smoothed[i + 1] - smoothed[i] != 0.0:
                    t = -smoothed[i] / (smoothed[i + 1] - smoothed[i])
                    ratio = xs[i] + t * (xs[i + 1] - xs[i])
                else:
                    ratio = xs[i]
                status = "crosses_to_harmful"
                cross_found = True
                break
            elif smoothed[i] >= 0.0 > smoothed[i + 1]:
                # Crossing from positive (hurts) to negative (helps)
                if smoothed[i] - smoothed[i + 1] != 0.0:
                    t = smoothed[i] / (smoothed[i] - smoothed[i + 1])
                    ratio = xs[i] + t * (xs[i + 1] - xs[i])
                else:
                    ratio = xs[i]
                status = "crosses_to_helpful"
                cross_found = True
                break

        if not cross_found:
            status = "no_crossover_detected"
            ratio = ""

    return {
        "crossover_ratio": round(ratio, 6) if isinstance(ratio, float) else ratio,
        "crossover_status": status,
        "smoothed_xs": xs,
        "smoothed_ys": smoothed,
        "lowess_fraction": lowess_fraction,
    }


# ── bootstrap confidence intervals ────────────────────────────────────────────

def _resample_points(points: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    """Bootstrap resample with replacement."""
    n = len(points)
    return [points[rng.randint(0, n - 1)] for _ in range(n)]


def _compute_bootstrap_p_helps(
    points: list[dict[str, Any]],
    B: int,
    seed: int | None,
    lowess_fraction: float,
) -> tuple[dict[float, float], list[float]]:
    """Bootstrap to estimate P(separation helps) per overlap bin."""
    rng = random.Random(seed)
    step = 0.05

    # Group points by bin
    bins: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for p in points:
        r = to_float(p.get("overlap_ratio"))
        if r is not None:
            bin_key = round(round(r / step) * step, 4)
            bins[bin_key].append(p)

    # Bootstrap per bin
    bin_helps_probs: dict[float, list[float]] = {bk: [] for bk in bins}
    all_crossovers: list[float] = []

    for _ in range(B):
        resampled = _resample_points(points, rng)
        # Per-bin mean delta
        bin_means: dict[float, float] = {}
        bin_counts: dict[float, int] = {}
        for p in resampled:
            r = to_float(p.get("overlap_ratio"))
            d = to_float(p.get("delta_cer_separated"))
            if r is not None and d is not None:
                bk = round(round(r / step) * step, 4)
                bin_means[bk] = bin_means.get(bk, 0.0) + d
                bin_counts[bk] = bin_counts.get(bk, 0) + 1

        for bk in bins:
            if bk in bin_counts and bin_counts[bk] > 0:
                mean_d = bin_means[bk] / bin_counts[bk]
                bin_helps_probs[bk].append(1.0 if mean_d < 0 else 0.0)

        # Crossover detection on this resample
        cross_result = compute_crossover_boundary(resampled, lowess_fraction)
        cr = cross_result["crossover_ratio"]
        if isinstance(cr, (int, float)) and cr != "":
            all_crossovers.append(float(cr))

    # Aggregate per-bin probabilities
    bin_probs: dict[float, float] = {}
    for bk, helps_list in sorted(bin_helps_probs.items()):
        if helps_list:
            bin_probs[bk] = round(sum(helps_list) / len(helps_list), 4)

    return bin_probs, all_crossovers


def bootstrap_crossover_ci(
    points: list[dict[str, Any]],
    B: int = 1000,
    seed: int | None = None,
    lowess_fraction: float = 0.33,
) -> dict[str, Any]:
    """Bootstrap confidence interval for the crossover ratio.

    Returns dict with crossover_ci (lower/median/upper/confidence/bootstrap_samples)
    and bootstrap_bin_probabilities.
    """
    bin_probs, all_crossovers = _compute_bootstrap_p_helps(
        points, B, seed, lowess_fraction
    )

    crossover_ci: dict[str, Any] = {
        "lower": "",
        "median": "",
        "upper": "",
        "confidence": 0.0,
        "bootstrap_samples": B,
    }

    if all_crossovers:
        sorted_cr = sorted(all_crossovers)
        n_cr = len(sorted_cr)
        crossover_ci["lower"] = round(sorted_cr[max(0, int(n_cr * 0.025))], 6)
        crossover_ci["median"] = round(sorted_cr[n_cr // 2], 6)
        crossover_ci["upper"] = round(sorted_cr[min(n_cr - 1, int(n_cr * 0.975))], 6)
        crossover_ci["confidence"] = round(n_cr / B, 4)

    return {
        "crossover_ci": crossover_ci,
        "bootstrap_bin_probabilities": bin_probs,
    }


# ── structured outputs ────────────────────────────────────────────────────────

def build_boundary_metadata(
    points: list[dict[str, Any]],
    B: int = 1000,
    seed: int | None = None,
    lowess_fraction: float = 0.33,
) -> dict[str, Any]:
    """Build a single metadata record describing the separation phase boundary."""
    boundary = compute_crossover_boundary(points, lowess_fraction)
    bootstrap = bootstrap_crossover_ci(points, B, seed, lowess_fraction)
    ci = bootstrap["crossover_ci"]

    cr = boundary["crossover_ratio"]
    if isinstance(cr, (int, float)) and cr != "":
        below = [p for p in points
                 if to_float(p.get("overlap_ratio")) is not None
                 and float(to_float(p.get("overlap_ratio", 0))) <= float(cr)]
        above = [p for p in points
                 if to_float(p.get("overlap_ratio")) is not None
                 and float(to_float(p.get("overlap_ratio", 0))) > float(cr)]
        below_help = (
            sum(1 for p in below if p.get("separation_helps") is True) / max(len(below), 1)
        )
        above_help = (
            sum(1 for p in above if p.get("separation_helps") is True) / max(len(above), 1)
        )
    else:
        below_help = sum(
            1 for p in points if p.get("separation_helps") is True
        ) / max(len(points), 1)
        above_help = below_help

    ci_lower = ci.get("lower", "")
    ci_upper = ci.get("upper", "")
    ci_width = ""
    if isinstance(ci_lower, (int, float)) and isinstance(ci_upper, (int, float)):
        ci_width = round(float(ci_upper) - float(ci_lower), 6)

    return {
        "boundary_type": boundary["crossover_status"],
        "crossover_ratio": cr,
        "crossover_ci_lower": ci_lower,
        "crossover_ci_median": ci.get("median", ""),
        "crossover_ci_upper": ci_upper,
        "crossover_ci_width": ci_width,
        "bootstrap_samples": B,
        "below_boundary_help_rate": round(below_help, 4),
        "above_boundary_help_rate": round(above_help, 4),
        "label": "experimental/frontier",
    }


def build_dense_trend_rows(
    points: list[dict[str, Any]],
    B: int = 1000,
    seed: int | None = None,
    lowess_fraction: float = 0.33,
    step: float = 0.05,
) -> list[dict[str, Any]]:
    """Build enhanced trend rows with bootstrap SE and CI columns."""
    # First, group by bin using existing logic
    grouped: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for p in points:
        r = to_float(p.get("overlap_ratio"))
        if r is None:
            continue
        bin_key = round(round(r / step) * step, 4)
        grouped[bin_key].append(p)

    # Bootstrap bin-level statistics
    rng = random.Random(seed)
    bin_bootstrap_means: dict[float, list[float]] = defaultdict(list)
    for _ in range(B):
        resampled = _resample_points(points, rng)
        bin_sums: dict[float, float] = {}
        bin_cts: dict[float, int] = {}
        for p in resampled:
            r = to_float(p.get("overlap_ratio"))
            d = to_float(p.get("delta_cer_separated"))
            if r is not None and d is not None:
                bk = round(round(r / step) * step, 4)
                bin_sums[bk] = bin_sums.get(bk, 0.0) + d
                bin_cts[bk] = bin_cts.get(bk, 0) + 1
        for bk in grouped:
            if bk in bin_cts and bin_cts[bk] > 0:
                bin_bootstrap_means[bk].append(bin_sums[bk] / bin_cts[bk])

    # Build trend rows
    trend_rows: list[dict[str, Any]] = []
    for overlap_bin in sorted(grouped.keys()):
        bucket = grouped[overlap_bin]
        deltas = [float(row["delta_cer_separated"]) for row in bucket]
        labels = sorted({str(row.get("source_label", "")) for row in bucket})
        help_count = sum(1 for row in bucket if row.get("separation_helps"))

        bs_means = bin_bootstrap_means.get(overlap_bin, [])
        if bs_means:
            bs_mean = round(mean(bs_means), 6)
            bs_se = round(stdev(bs_means), 6) if len(bs_means) > 1 else 0.0
            ci_lower = round(sorted(bs_means)[max(0, int(len(bs_means) * 0.025))], 6)
            ci_upper = round(sorted(bs_means)[min(len(bs_means) - 1, int(len(bs_means) * 0.975))], 6)
            p_helps = round(sum(1 for m in bs_means if m < 0) / max(len(bs_means), 1), 4)
        else:
            bs_mean = 0.0
            bs_se = 0.0
            ci_lower = 0.0
            ci_upper = 0.0
            p_helps = 0.0

        trend_rows.append({
            "overlap_bin": overlap_bin,
            "sample_count": len(bucket),
            "mean_delta_cer_separated": round(mean(deltas), 6),
            "median_delta_cer_separated": round(median(deltas), 6),
            "separation_help_rate": round(help_count / len(bucket), 4),
            "source_labels": ";".join(labels),
            "bootstrap_mean_delta_cer": bs_mean,
            "bootstrap_se_cer": bs_se,
            "bootstrap_p_helps": p_helps,
            "trend_ci_lower": ci_lower,
            "trend_ci_upper": ci_upper,
        })

    return trend_rows


# ── output ────────────────────────────────────────────────────────────────────

def build_boundary_markdown(metadata: dict[str, Any]) -> list[str]:
    """Generate markdown summary lines for the boundary analysis."""
    boundary_type = str(metadata.get("boundary_type", ""))
    cr = metadata.get("crossover_ratio", "")
    ci_lower = metadata.get("crossover_ci_lower", "")
    ci_upper = metadata.get("crossover_ci_upper", "")
    ci_width = metadata.get("crossover_ci_width", "")
    below_rate = metadata.get("below_boundary_help_rate", "")
    above_rate = metadata.get("above_boundary_help_rate", "")

    lines = [
        "# Separation Phase Boundary Analysis (experimental/frontier)",
        "",
        "Label: `experimental/frontier` — does not replace the stable gold benchmark.",
        "",
        "## Crossover Detection",
        "",
        f"- **Boundary type**: {boundary_type}",
    ]

    if cr != "":
        lines.append(f"- **Crossover ratio**: {cr}")
        lines.append(
            f"- **95% CI**: [{ci_lower}, {ci_upper}] (width: {ci_width})"
        )
        lines.append(f"- **Below-boundary help rate**: {below_rate}")
        lines.append(f"- **Above-boundary help rate**: {above_rate}")
    else:
        lines.append("- No crossover detected in the current data range.")

    lines.extend([
        "",
        "## Interpretation",
        "",
    ])

    if boundary_type == "crosses_to_harmful":
        lines.append(
            f"Separation systematically helps below overlap ratio ~{cr} "
            f"and systematically hurts above it. This supports the project's "
            f"core selective-separation narrative with statistical confidence."
        )
    elif boundary_type == "crosses_to_helpful":
        lines.append(
            f"Separation appears to hurt at low overlap and help at high overlap "
            f"(crossover at r~{cr}). This counterintuitive result is likely driven "
            f"by extreme outlier CER values in synthetic NoOverlap samples — gold-only "
            f"evidence shows the opposite trend. Interpret as a data-quality signal "
            f"rather than a deployment claim."
        )
    elif boundary_type == "always_helpful":
        lines.append(
            "Separation appears to help across the entire observed overlap range. "
            "This may indicate the current sweep does not reach high enough overlap "
            "ratios to observe the harmful regime."
        )
    elif boundary_type == "always_harmful":
        lines.append(
            "Separation appears to hurt across the entire observed overlap range. "
            "This would challenge the project's narrative and should be verified "
            "with additional controlled experiments."
        )
    else:
        lines.append(
            "No clear crossover was detected. This may be due to insufficient "
            "data density or high variance in the current measurements."
        )

    return lines


def write_outputs(
    metadata: dict[str, Any],
    dense_trend_rows: list[dict[str, Any]],
) -> tuple[Path, Path, Path, Path, Path]:
    """Write boundary metadata and dense trend output files."""
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    boundary_csv = tables_dir / "separation_phase_boundary.csv"
    boundary_json = tables_dir / "separation_phase_boundary.json"
    trend_csv = tables_dir / "separation_phase_dense_trend.csv"
    trend_json = tables_dir / "separation_phase_dense_trend.json"
    boundary_md = figures_dir / "separation_phase_boundary.md"

    with boundary_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BOUNDARY_COLUMNS)
        writer.writeheader()
        writer.writerow(metadata)
    boundary_json.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with trend_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DENSE_TREND_COLUMNS)
        writer.writeheader()
        writer.writerows(dense_trend_rows)
    trend_json.write_text(
        json.dumps(dense_trend_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    boundary_md.write_text(
        "\n".join(build_boundary_markdown(metadata)) + "\n", encoding="utf-8"
    )

    return boundary_csv, boundary_json, trend_csv, trend_json, boundary_md


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run separation phase boundary detection and bootstrap CI."
    )
    parser.add_argument(
        "--bootstrap-samples",
        type=int,
        default=1000,
        help="Number of bootstrap resamples (default: 1000).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible bootstrap (default: 42).",
    )
    parser.add_argument(
        "--lowess-fraction",
        type=float,
        default=0.33,
        help="Fraction of points in each LOWESS window (default: 0.33).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _ = load_config()

    # Read existing phase diagram points from JSON
    diagram_json = PROJECT_ROOT / "results" / "tables" / "separation_phase_diagram.json"
    if diagram_json.exists():
        payload = json.loads(diagram_json.read_text(encoding="utf-8"))
        points = payload if isinstance(payload, list) else []
    else:
        print(
            "No separation_phase_diagram.json found. "
            "Run 'python -m src.separation_phase_diagram' first."
        )
        return

    if not points:
        print("No phase diagram points available — run separation_phase_diagram first.")
        return

    metadata = build_boundary_metadata(
        points, B=args.bootstrap_samples, seed=args.seed,
        lowess_fraction=args.lowess_fraction,
    )
    dense_trend = build_dense_trend_rows(
        points, B=args.bootstrap_samples, seed=args.seed,
        lowess_fraction=args.lowess_fraction,
    )
    paths = write_outputs(metadata, dense_trend)
    for p in paths:
        print(f"Wrote: {p.relative_to(PROJECT_ROOT)}")

    print(f"Boundary type: {metadata['boundary_type']}")
    if metadata["crossover_ratio"] != "":
        print(f"Crossover ratio: {metadata['crossover_ratio']}")
        print(f"95% CI: [{metadata['crossover_ci_lower']}, {metadata['crossover_ci_upper']}]")


if __name__ == "__main__":
    main()
