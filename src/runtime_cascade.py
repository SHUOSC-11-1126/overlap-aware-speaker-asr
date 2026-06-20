"""Runtime Compute Cascade: tiny→base escalation -- experimental/frontier (Issue #863).

Research question (pre-registered):
  The Model Scale Analysis (#859) showed base eliminates the separation tax
  (CER 0.200 vs tiny 0.467) but costs more compute.  This module builds an
  ACTUAL runtime cascade: run tiny on all segments, escalate only high-risk
  segments (by compression_ratio) to base, and trace the Pareto frontier of
  CER vs compute.

  RQ1 (recovery): What fraction of the tiny→base CER gap does a cascade with
     20% escalation rate recover?
  RQ2 (signal quality): Does CR from tiny correctly identify which segments
     need base-level processing?
  RQ3 (Pareto): Does the cascade Pareto-dominate both fixed-tiny and fixed-base?

  Hypotheses:
    H1: 20% escalation recovers >80% of the CER gap.
    H2: CR-threshold escalation outperforms random escalation at the same rate.
    H3: The cascade Pareto-dominates (lower CER than tiny at same compute, or
        lower compute than base at same CER).

  Labels: experimental/frontier. References are synthetic/silver. Models: tiny
  + base. Stable tables untouched; outputs go to results/frontier/runtime_cascade/.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .evaluate_cer import compute_cer
from .generate_synthetic_overlap import build_mixture, read_mono_audio
from .separation_tax_phase import (
    load_snippet_reference,
    select_pairs,
    trim_silence,
    transcribe_with_signals,
)

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "runtime_cascade"

# Risk thresholds to sweep: escalate if CR > threshold
RISK_THRESHOLDS = [0.0, 0.5, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5, 2.0, 2.4, 3.0, 5.0, 10.0]


def run(
    out_dir: Path,
    num_pairs: int = 5,
    quick: bool = False,
) -> dict[str, Any]:
    """Run the runtime cascade experiment."""
    import whisper

    out_dir.mkdir(parents=True, exist_ok=True)
    model_tiny = whisper.load_model("tiny")
    model_base = whisper.load_model("base")

    ratios = [0.0, 0.15, 0.35, 0.60, 0.90] if quick else [
        0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45,
        0.50, 0.60, 0.70, 0.80, 0.90,
    ]
    thresholds = RISK_THRESHOLDS[:6] if quick else RISK_THRESHOLDS
    plans = select_pairs(num_pairs)
    print(f"[cascade] pairs={len(plans)} ratios={len(ratios)} thresholds={len(thresholds)}", flush=True)

    rows: list[dict[str, Any]] = []
    curve_path = out_dir / "cascade_curve.csv"

    # Build fieldnames
    fieldnames = [
        "pair_id", "con", "pro", "overlap_ratio",
        "cer_tiny", "cer_base", "cr_tiny",
        "runtime_tiny", "runtime_base",
    ]
    for thr in thresholds:
        fieldnames += [f"cer_cascade_{thr}", f"escalate_frac_{thr}", f"runtime_cascade_{thr}"]

    with curve_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()

        for pi, plan in enumerate(plans):
            s1 = read_mono_audio(plan.con_path)
            s2 = read_mono_audio(plan.pro_path)
            ref = plan.con_text + plan.pro_text

            for ratio in ratios:
                mixed, track1, track2, _ = build_mixture(s1, s2, ratio)
                t1_trim = trim_silence(track1)
                t2_trim = trim_silence(track2)

                # Run tiny on both tracks
                t0 = time.perf_counter()
                s1_tiny = transcribe_with_signals(model_tiny, t1_trim, "greedy")
                s2_tiny = transcribe_with_signals(model_tiny, t2_trim, "greedy")
                runtime_tiny = time.perf_counter() - t0

                # Run base on both tracks
                t0 = time.perf_counter()
                s1_base = transcribe_with_signals(model_base, t1_trim, "greedy")
                s2_base = transcribe_with_signals(model_base, t2_trim, "greedy")
                runtime_base = time.perf_counter() - t0

                # CR from tiny (risk signal)
                cr_s1 = s1_tiny["max_compression_ratio"]
                cr_s2 = s2_tiny["max_compression_ratio"]
                max_cr = max(cr_s1, cr_s2)

                # CER of fixed strategies
                cer_tiny = compute_cer(ref, s1_tiny["text"] + s2_tiny["text"])["cer"]
                cer_base = compute_cer(ref, s1_base["text"] + s2_base["text"])["cer"]

                row: dict[str, Any] = {
                    "pair_id": pi, "con": plan.con_path.name, "pro": plan.pro_path.name,
                    "overlap_ratio": ratio,
                    "cer_tiny": round(cer_tiny, 6),
                    "cer_base": round(cer_base, 6),
                    "cr_tiny": round(max_cr, 4),
                    "runtime_tiny": round(runtime_tiny, 3),
                    "runtime_base": round(runtime_base, 3),
                }

                # Cascade at each threshold
                for thr in thresholds:
                    # Escalate tracks where CR > threshold
                    escalate_s1 = cr_s1 > thr
                    escalate_s2 = cr_s2 > thr

                    text_s1 = s1_base["text"] if escalate_s1 else s1_tiny["text"]
                    text_s2 = s2_base["text"] if escalate_s2 else s2_tiny["text"]
                    cascade_text = text_s1 + text_s2
                    cer_cascade = compute_cer(ref, cascade_text)["cer"]

                    n_escalated = int(escalate_s1) + int(escalate_s2)
                    escalate_frac = n_escalated / 2.0
                    rt_cascade = runtime_tiny  # tiny runs on everything
                    if escalate_s1:
                        rt_cascade += (s1_base.get("runtime_sec", 0) or 0) - (s1_tiny.get("runtime_sec", 0) or 0)
                    if escalate_s2:
                        rt_cascade += (s2_base.get("runtime_sec", 0) or 0) - (s2_tiny.get("runtime_sec", 0) or 0)

                    row[f"cer_cascade_{thr}"] = round(cer_cascade, 6)
                    row[f"escalate_frac_{thr}"] = round(escalate_frac, 4)
                    row[f"runtime_cascade_{thr}"] = round(max(rt_cascade, runtime_tiny), 3)

                writer.writerow(row)
                rows.append(row)

            fh.flush()
            print(f"[cascade] pair {pi + 1}/{len(plans)} done", flush=True)

    summary = analyze(rows, thresholds, out_dir)
    print(f"[cascade] n={len(rows)} wrote {OUT_DIR.relative_to(PROJECT_ROOT)}", flush=True)
    return summary


def analyze(
    rows: list[dict[str, Any]], thresholds: list[float], out_dir: Path,
) -> dict[str, Any]:
    """Analyze cascade results."""

    def _mean(xs: list[float]) -> float:
        vals = [x for x in xs if x == x]
        return round(sum(vals) / len(vals), 6) if vals else 0.0

    mean_tiny = _mean([float(r["cer_tiny"]) for r in rows])
    mean_base = _mean([float(r["cer_base"]) for r in rows])
    gap = mean_tiny - mean_base  # positive = base is better

    # Per-threshold analysis
    frontier_points = []
    for thr in thresholds:
        cer_vals = [float(r[f"cer_cascade_{thr}"]) for r in rows]
        esc_vals = [float(r[f"escalate_frac_{thr}"]) for r in rows]
        rt_vals = [float(r[f"runtime_cascade_{thr}"]) for r in rows]
        mean_cer = _mean(cer_vals)
        mean_esc = _mean(esc_vals)
        mean_rt = _mean(rt_vals)
        recovery = (mean_tiny - mean_cer) / gap if gap > 0 else 0.0
        frontier_points.append({
            "threshold": thr,
            "mean_cer": mean_cer,
            "mean_escalate_frac": mean_esc,
            "mean_runtime_sec": mean_rt,
            "gap_recovery": round(recovery, 4),
        })

    # Find the ~20% escalation point
    target_esc = 0.2
    closest = min(frontier_points, key=lambda p: abs(p["mean_escalate_frac"] - target_esc))

    # Random escalation baseline: what if we escalated 20% randomly?
    # (approximate: the mean CER at any threshold is a weighted average of tiny/base)
    # We can compute this as: mean_cer_random = 0.2 * mean_base + 0.8 * mean_tiny
    random_cer = round(0.2 * mean_base + 0.8 * mean_tiny, 6)

    # Pareto check: is cascade better than both fixed strategies at same compute?
    tiny_rt = _mean([float(r["runtime_tiny"]) for r in rows])
    base_rt = _mean([float(r["runtime_base"]) for r in rows])

    summary = {
        "n": len(rows),
        "fixed_tiny_cer": mean_tiny,
        "fixed_base_cer": mean_base,
        "cer_gap": round(gap, 6),
        "frontier": frontier_points,
        "h1_twenty_pct": {
            "target_escalation": target_esc,
            "actual_escalation": closest["mean_escalate_frac"],
            "threshold": closest["threshold"],
            "cascade_cer": closest["mean_cer"],
            "gap_recovery": closest["gap_recovery"],
            "h1_confirmed": closest["gap_recovery"] > 0.8,
        },
        "h2_vs_random": {
            "cascade_cer_at_20pct": closest["mean_cer"],
            "random_escalation_cer": random_cer,
            "cascade_beats_random": closest["mean_cer"] < random_cer,
        },
        "compute": {
            "tiny_runtime_sec": tiny_rt,
            "base_runtime_sec": base_rt,
            "speedup_base_vs_tiny": round(base_rt / max(tiny_rt, 0.001), 2),
        },
    }

    # Write outputs
    (out_dir / "cascade_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_frontier_csv(frontier_points, out_dir / "pareto_frontier.csv")

    try:
        render_figure(frontier_points, summary, out_dir)
    except Exception as exc:
        print(f"[cascade] figure skipped: {exc}", flush=True)

    return summary


def _write_frontier_csv(points: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(points[0].keys()))
        writer.writeheader()
        writer.writerows(points)


def render_figure(
    frontier: list[dict[str, Any]], summary: dict[str, Any], out_dir: Path,
) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Panel 1: Pareto frontier — CER vs escalation rate
    cer = [p["mean_cer"] for p in frontier]
    esc = [p["mean_escalate_frac"] for p in frontier]
    ax1.plot(esc, cer, "-o", color="#4c78a8", label="cascade", markersize=5)
    ax1.axhline(summary["fixed_tiny_cer"], color="#e45756", ls="--", label=f"fixed tiny ({summary['fixed_tiny_cer']:.3f})")
    ax1.axhline(summary["fixed_base_cer"], color="#54a24b", ls="--", label=f"fixed base ({summary['fixed_base_cer']:.3f})")
    ax1.axvline(0.2, color="gray", ls=":", alpha=0.5, label="20% target")
    ax1.set_xlabel("Escalation fraction (segments sent to base)")
    ax1.set_ylabel("Mean CER")
    ax1.set_title("Pareto Frontier: CER vs Compute")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)

    # Panel 2: Gap recovery vs threshold
    thresholds = [p["threshold"] for p in frontier]
    recovery = [p["gap_recovery"] for p in frontier]
    ax2.plot(thresholds, recovery, "-s", color="#f58518", markersize=5)
    ax2.axhline(0.8, color="#54a24b", ls="--", label="80% recovery target")
    ax2.set_xlabel("CR threshold (escalate if CR > threshold)")
    ax2.set_ylabel("Gap recovery (fraction of tiny→base improvement)")
    ax2.set_title("Recovery vs Risk Threshold")
    ax2.legend()
    ax2.grid(alpha=0.3)

    fig.suptitle("Runtime Compute Cascade: tiny→base escalation", fontsize=11)
    fig.tight_layout()
    fig_path = out_dir / "cascade_analysis.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    return fig_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runtime Compute Cascade (frontier).")
    parser.add_argument("--pairs", type=int, default=5)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(Path(args.out_dir), num_pairs=args.pairs, quick=args.quick)


if __name__ == "__main__":
    main()
