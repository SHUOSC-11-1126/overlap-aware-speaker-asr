"""Whisper Model Scale Analysis -- experimental/frontier (Issue #859).

Research question (pre-registered):
  ALL 29 existing frontier studies use Whisper tiny exclusively.  This module
  tests whether the key findings — separation tax, hallucination rate, signal
  discriminability — generalize to larger models (base, and small if available).

  RQ1 (hallucination rate): Does the catastrophic tail rate (CER > 1.0) decrease
     monotonically from tiny → base → small?
  RQ2 (phase boundary): Does the separation-tax crossover r* move leftward
     (separation helps at lower overlap) for larger models?
  RQ3 (signal paradox): Does compression_ratio become LESS discriminative for
     larger models because they're confident on more inputs?

  Hypotheses:
    H1: Tail rate decreases: tiny > base > small.
    H2: Crossover r* moves left for larger models.
    H3: CR AUC decreases for larger models (signal paradox).

  Labels: experimental/frontier. References are synthetic/silver. CER is post-hoc
  only. Stable tables untouched; outputs go to results/frontier/model_scale/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT
from .evaluate_cer import compute_cer, repetition_count_from_text
from .generate_synthetic_overlap import build_mixture, read_mono_audio
from .reference_free_qe import rank_auc, spearman_corr
from .separation_tax_phase import (
    CATASTROPHIC_CER,
    _to_float,
    load_snippet_reference,
    select_pairs,
    tail_rate,
    trim_silence,
    transcribe_with_signals,
)

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "model_scale"


def run(
    out_dir: Path,
    num_pairs: int = 5,
    model_names: list[str] | None = None,
    quick: bool = False,
) -> dict[str, Any]:
    """Run the model scale analysis across Whisper model sizes."""
    import whisper

    if model_names is None:
        model_names = ["tiny", "base"]

    out_dir.mkdir(parents=True, exist_ok=True)

    # Load models
    models = {}
    for name in model_names:
        print(f"[scale] loading Whisper-{name}...", flush=True)
        try:
            models[name] = whisper.load_model(name)
        except Exception as exc:
            print(f"[scale] FAILED to load {name}: {exc}", flush=True)

    if not models:
        raise RuntimeError("No models loaded")

    ratios = [0.0, 0.15, 0.35, 0.60, 0.90] if quick else [
        0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45,
        0.50, 0.60, 0.70, 0.80, 0.90,
    ]
    plans = select_pairs(num_pairs)
    active_models = sorted(models.keys())
    print(f"[scale] models={active_models} pairs={len(plans)} ratios={len(ratios)}", flush=True)

    # Build fieldnames
    fieldnames = ["pair_id", "con", "pro", "overlap_ratio"]
    for m in active_models:
        fieldnames += [
            f"cer_mixed_{m}", f"cer_sep_{m}", f"cer_sep_trim_{m}",
            f"cr_mixed_{m}", f"cr_sep_{m}",
            f"nsp_sep_{m}", f"rep_sep_{m}",
            f"nseg_mixed_{m}", f"nseg_sep_{m}",
            f"runtime_mixed_{m}", f"runtime_sep_{m}",
        ]

    rows: list[dict[str, Any]] = []
    curve_path = out_dir / "scale_curve.csv"

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

                row: dict[str, Any] = {
                    "pair_id": pi, "con": plan.con_path.name,
                    "pro": plan.pro_path.name, "overlap_ratio": ratio,
                }

                for mname, model in models.items():
                    # Mixed
                    mx = transcribe_with_signals(model, mixed, "greedy")
                    # Separated (trimmed)
                    s1r = transcribe_with_signals(model, t1_trim, "greedy")
                    s2r = transcribe_with_signals(model, t2_trim, "greedy")
                    sep_text = s1r["text"] + s2r["text"]

                    cer_m = compute_cer(ref, mx["text"])["cer"]
                    cer_s = compute_cer(ref, sep_text)["cer"]

                    cr_m = mx["max_compression_ratio"]
                    cr_s = max(s1r["max_compression_ratio"], s2r["max_compression_ratio"])
                    nsp_s = max(s1r["max_no_speech_prob"], s2r["max_no_speech_prob"])
                    rep_s = s1r["repetition_count"] + s2r["repetition_count"]

                    row[f"cer_mixed_{mname}"] = round(cer_m, 6)
                    row[f"cer_sep_{mname}"] = round(cer_s, 6)
                    row[f"cr_mixed_{mname}"] = round(cr_m, 4)
                    row[f"cr_sep_{mname}"] = round(cr_s, 4)
                    row[f"nsp_sep_{mname}"] = round(nsp_s, 4)
                    row[f"rep_sep_{mname}"] = rep_s
                    row[f"nseg_mixed_{mname}"] = mx["n_segments"]
                    row[f"nseg_sep_{mname}"] = s1r["n_segments"] + s2r["n_segments"]
                    row[f"runtime_mixed_{mname}"] = round(mx.get("runtime_sec", 0), 3)
                    row[f"runtime_sep_{mname}"] = round(
                        s1r.get("runtime_sec", 0) + s2r.get("runtime_sec", 0), 3,
                    )

                writer.writerow(row)
                rows.append(row)

            fh.flush()
            print(f"[scale] pair {pi + 1}/{len(plans)} done", flush=True)

    summary = analyze(rows, active_models, out_dir)
    print(f"[scale] n={len(rows)} models={active_models} wrote {OUT_DIR.relative_to(PROJECT_ROOT)}", flush=True)
    return summary


def analyze(
    rows: list[dict[str, Any]], models: list[str], out_dir: Path,
) -> dict[str, Any]:
    """Analyze model scale results."""

    def _mean(xs: list[float]) -> float:
        vals = [x for x in xs if x == x]
        return round(sum(vals) / len(vals), 6) if vals else 0.0

    summary: dict[str, Any] = {"n": len(rows), "models": models, "per_model": {}}

    for m in models:
        cer_mixed = [float(r[f"cer_mixed_{m}"]) for r in rows]
        cer_sep = [float(r[f"cer_sep_{m}"]) for r in rows]
        cr_sep = [float(r[f"cr_sep_{m}"]) for r in rows]
        nsp_sep = [float(r[f"nsp_sep_{m}"]) for r in rows]
        rep_sep = [float(r[f"rep_sep_{m}"]) for r in rows]

        # Tail rate
        tail_mixed = tail_rate(cer_mixed)
        tail_sep = tail_rate(cer_sep)

        # CR discriminability (AUC for detecting CER > 0.5)
        cr_labels = [1 if c > 0.5 else 0 for c in cer_sep]
        cr_auc = rank_auc(cr_sep, cr_labels) if any(cr_labels) and not all(cr_labels) else 0.5

        # Signal correlations
        spearman_cr = spearman_corr(cr_sep, cer_sep)
        spearman_nsp = spearman_corr(nsp_sep, cer_sep)

        # Per-overlap analysis
        ratios = sorted({float(r["overlap_ratio"]) for r in rows})
        per_ratio = []
        for ratio in ratios:
            at = [r for r in rows if float(r["overlap_ratio"]) == ratio]
            per_ratio.append({
                "overlap_ratio": ratio,
                "mean_cer_mixed": _mean([float(r[f"cer_mixed_{m}"]) for r in at]),
                "mean_cer_sep": _mean([float(r[f"cer_sep_{m}"]) for r in at]),
                "mean_cr_sep": _mean([float(r[f"cr_sep_{m}"]) for r in at]),
            })

        # Find crossover (where sep becomes better than mixed)
        delta_cer = [
            r[f"mean_cer_mixed"] - r[f"mean_cer_sep"] for r in per_ratio
        ]
        crossover = None
        for i, d in enumerate(delta_cer):
            if i > 0 and delta_cer[i - 1] <= 0 < d:
                crossover = per_ratio[i]["overlap_ratio"]
                break
        if crossover is None and delta_cer and delta_cer[0] > 0:
            crossover = per_ratio[0]["overlap_ratio"]

        summary["per_model"][m] = {
            "mean_cer_mixed": _mean(cer_mixed),
            "mean_cer_sep": _mean(cer_sep),
            "tail_rate_mixed": tail_mixed,
            "tail_rate_sep": tail_sep,
            "cr_auc_cer>0.5": round(cr_auc, 4),
            "spearman_cr_vs_cer": spearman_cr,
            "spearman_nsp_vs_cer": spearman_nsp,
            "crossover_ratio": crossover,
            "mean_runtime_sec": _mean([float(r[f"runtime_mixed_{m}"]) for r in rows]),
            "per_ratio": per_ratio,
        }

    # Cross-model comparison
    if len(models) >= 2:
        summary["cross_model"] = {}
        for m1, m2 in zip(models, models[1:]):
            p1 = summary["per_model"][m1]
            p2 = summary["per_model"][m2]
            summary["cross_model"][f"{m1}_vs_{m2}"] = {
                "cer_improvement": round(p1["mean_cer_sep"] - p2["mean_cer_sep"], 6),
                "tail_rate_change": round(p1["tail_rate_sep"] - p2["tail_rate_sep"], 6),
                "cr_auc_change": round(p2["cr_auc_cer>0.5"] - p1["cr_auc_cer>0.5"], 6),
                "runtime_multiplier": round(p2["mean_runtime_sec"] / max(p1["mean_runtime_sec"], 0.001), 2),
            }

    # Hypotheses
    if len(models) >= 2:
        h1_check = all(
            summary["per_model"][m1]["tail_rate_sep"] >= summary["per_model"][m2]["tail_rate_sep"]
            for m1, m2 in zip(models, models[1:])
        )
        summary["h1_tail_rate_decreasing"] = h1_check

        crossovers = [summary["per_model"][m].get("crossover_ratio") for m in models]
        valid_crossovers = [c for c in crossovers if c is not None]
        if len(valid_crossovers) >= 2:
            summary["h2_crossover_shifts_left"] = all(
                c1 >= c2 for c1, c2 in zip(valid_crossovers, valid_crossovers[1:])
            )
        else:
            summary["h2_crossover_shifts_left"] = None

        aucs = [summary["per_model"][m]["cr_auc_cer>0.5"] for m in models]
        summary["h3_signal_paradox"] = all(
            a1 >= a2 for a1, a2 in zip(aucs, aucs[1:])
        )

    # Write outputs
    (out_dir / "scale_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    try:
        render_figure(summary, out_dir)
    except Exception as exc:
        print(f"[scale] figure skipped: {exc}", flush=True)

    return summary


def render_figure(summary: dict[str, Any], out_dir: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    models = summary["models"]
    colors = {"tiny": "#e45756", "base": "#4c78a8", "small": "#54a24b"}

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # Panel 1: CER vs overlap ratio per model
    ax1 = axes[0]
    for m in models:
        pr = summary["per_model"][m]["per_ratio"]
        ratios = [r["overlap_ratio"] for r in pr]
        cer_sep = [r["mean_cer_sep"] for r in pr]
        ax1.plot(ratios, cer_sep, "-o", color=colors.get(m, "gray"),
                 label=f"{m}", markersize=4)
    ax1.set_xlabel("overlap ratio")
    ax1.set_ylabel("Mean CER (separated)")
    ax1.set_title("Separation Tax by Model Size")
    ax1.legend()
    ax1.grid(alpha=0.3)

    # Panel 2: CR AUC per model
    ax2 = axes[1]
    aucs = [summary["per_model"][m]["cr_auc_cer>0.5"] for m in models]
    ax2.bar(models, aucs, color=[colors.get(m, "gray") for m in models])
    ax2.set_ylabel("AUC (CR detecting CER > 0.5)")
    ax2.set_title("Signal Discriminability")
    ax2.axhline(0.5, color="black", ls="--", alpha=0.5, label="random")
    ax2.legend()
    ax2.grid(alpha=0.3)

    # Panel 3: Tail rate per model
    ax3 = axes[2]
    tails_sep = [summary["per_model"][m]["tail_rate_sep"] for m in models]
    tails_mixed = [summary["per_model"][m]["tail_rate_mixed"] for m in models]
    x = np.arange(len(models))
    w = 0.35
    ax3.bar(x - w / 2, tails_mixed, w, label="mixed", color="#e45756", alpha=0.7)
    ax3.bar(x + w / 2, tails_sep, w, label="separated", color="#4c78a8", alpha=0.7)
    ax3.set_xticks(x)
    ax3.set_xticklabels(models)
    ax3.set_ylabel("Catastrophic tail rate (CER > 1.0)")
    ax3.set_title("Hallucination Rate")
    ax3.legend()
    ax3.grid(alpha=0.3)

    fig.suptitle("Whisper Model Scale Analysis: Do tiny-based findings generalize?", fontsize=11)
    fig.tight_layout()
    fig_path = out_dir / "model_scale_analysis.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    return fig_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Whisper Model Scale Analysis (frontier).")
    parser.add_argument("--pairs", type=int, default=5)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(Path(args.out_dir), num_pairs=args.pairs, quick=args.quick)


if __name__ == "__main__":
    main()
