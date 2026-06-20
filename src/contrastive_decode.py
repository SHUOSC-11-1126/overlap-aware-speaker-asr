"""Contrastive Decoding via temperature-fallback divergence -- experimental/frontier.

Research question (pre-registered, Issue #857):
  Every existing router/gate in the project is REACTIVE — it detects hallucination
  after decoding and routes around it.  This module tests a PROACTIVE approach:
  run Whisper twice on the same audio (greedy vs temperature-fallback), compare
  the outputs, and use the DIVERGENCE between them as both a hallucination
  detector and a correction mechanism.

  Whisper's temperature-fallback is its built-in anti-hallucination mechanism:
  when a greedy decode looks degenerate (high compression_ratio or low logprob),
  it retries at higher temperatures.  If greedy and fallback agree → the decode
  is stable (high confidence).  If they disagree → the decode is unstable (likely
  hallucinated).  We test whether:

  RQ1 (detection): Does greedy-vs-fallback divergence predict hallucination
     better than compression_ratio alone?
  RQ2 (correction): Does a segment-level hybrid (use fallback text where greedy
     and fallback diverge, greedy text elsewhere) reduce CER vs pure greedy?
  RQ3 (causal): Is divergence concentrated in the segments that drive the
     separation tax (i.e., the hallucination-prone silence-tail segments)?

  Hypotheses:
    H1: Divergent segments have higher CER than agreeing segments.
    H2: The segment-level hybrid has lower mean CER than pure greedy on
        high-overlap (hallucination-prone) samples.
    H3: Divergence rate increases at low overlap ratios (where silence tails
        cause hallucination).

  Labels: experimental/frontier. Uses existing phase_curve.csv (greedy + fallback
  rows already exist — no new ASR needed for the initial analysis). For the
  segment-level hybrid, we re-run on a subset. References are synthetic/silver.
  Stable tables untouched; outputs go to results/frontier/contrastive_decode/.

  What is useful even if hypotheses fail:
    If greedy-fallback agreement doesn't predict hallucination, that means
    Whisper's anti-hallucination mechanism fires even on good segments (too
    conservative) or misses hallucinations (too lenient). Either is a finding.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT
from .evaluate_cer import compute_cer
from .generate_synthetic_overlap import build_mixture, read_mono_audio
from .reference_free_qe import rank_auc, spearman_corr
from .separation_tax_phase import (
    _to_float,
    load_snippet_reference,
    select_pairs,
    trim_silence,
    transcribe_with_signals,
)

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "contrastive_decode"


# ---- Pure divergence logic (unit-testable, no I/O) --------------------------------

def text_divergence(text_a: str, text_b: str) -> float:
    """Measure how much two texts disagree.  Returns CER between them (0 = identical)."""
    if not text_a and not text_b:
        return 0.0
    if not text_a or not text_b:
        return 1.0
    return compute_cer(text_a, text_b)["cer"]


def is_divergent(text_a: str, text_b: str, threshold: float = 0.1) -> bool:
    """Binary: do the two decodes disagree beyond threshold?"""
    return text_divergence(text_a, text_b) > threshold


def segment_hybrid(
    greedy_text: str,
    fallback_text: str,
    divergence_threshold: float = 0.1,
) -> str:
    """Produce a hybrid transcript: use fallback text when greedy and fallback
    diverge (fallback is Whisper's anti-hallucination output), greedy otherwise.

    For simplicity, operates on whole-transcript level (not segment-level) since
    the phase_curve data doesn't have per-segment alignment.
    """
    div = text_divergence(greedy_text, fallback_text)
    if div > divergence_threshold:
        return fallback_text  # fallback is the "cleaned" version
    return greedy_text  # they agree, use greedy (deterministic, reproducible)


def contrastive_confidence(
    greedy_text: str,
    fallback_text: str,
    greedy_cr: float,
    fallback_cr: float,
) -> dict[str, float]:
    """Compute contrastive confidence signals from dual-decode comparison.

    Returns multiple signals for analysis.
    """
    div = text_divergence(greedy_text, fallback_text)
    return {
        "divergence": div,
        "is_divergent": 1.0 if div > 0.1 else 0.0,
        "cr_greedy": greedy_cr,
        "cr_fallback": fallback_cr,
        "cr_delta": greedy_cr - fallback_cr,  # positive = fallback has lower CR (better)
        # Combined signal: divergence + CR improvement
        "contrastive_signal": div * (1.0 + max(0, greedy_cr - fallback_cr)),
    }


# ---- Driver (uses existing phase_curve + re-runs on subset) ----------------------

def analyze_existing_phase_curve(out_dir: Path) -> dict[str, Any]:
    """Analyze greedy-vs-fallback divergence using existing phase_curve.csv.

    This requires NO new ASR — the phase study already ran both configs.
    """
    phase_path = PROJECT_ROOT / "results" / "frontier" / "separation_tax" / "phase_curve.csv"
    if not phase_path.exists():
        raise FileNotFoundError(f"Missing phase curve: {phase_path}")

    with phase_path.open("r", newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    # Group by (pair_id, overlap_ratio) — each has a greedy and fallback row
    from collections import defaultdict
    grouped: dict[tuple, dict[str, dict[str, Any]]] = defaultdict(dict)
    for r in rows:
        key = (r["pair_id"], r["overlap_ratio"])
        config = r.get("config", "greedy")
        grouped[key][config] = r

    # Analyze divergence
    analyses = []
    for (pair_id, ratio), configs in grouped.items():
        if "greedy" not in configs or "fallback" not in configs:
            continue
        g = configs["greedy"]
        f = configs["fallback"]

        # The phase_curve doesn't store per-config text, but it stores CER values
        # and signal values.  We can compare SIGNALS as a proxy for divergence.
        cr_g = max(_to_float(g.get("cr_sep1", 0)), _to_float(g.get("cr_sep2", 0)))
        cr_f = max(_to_float(f.get("cr_sep1", 0)), _to_float(f.get("cr_sep2", 0)))
        nsp_g = max(_to_float(g.get("nsp_sep1", 0)), _to_float(g.get("nsp_sep2", 0)))
        nsp_f = max(_to_float(f.get("nsp_sep1", 0)), _to_float(f.get("nsp_sep2", 0)))

        # Signal divergence (proxy for text divergence)
        cr_div = abs(cr_g - cr_f)
        nsp_div = abs(nsp_g - nsp_f)

        cer_g_mixed = _to_float(g.get("cer_mixed", 0))
        cer_g_sep = _to_float(g.get("cer_sep", 0))
        cer_f_mixed = _to_float(f.get("cer_mixed", 0))
        cer_f_sep = _to_float(f.get("cer_sep", 0))

        analyses.append({
            "pair_id": pair_id,
            "overlap_ratio": float(ratio),
            "cr_greedy": round(cr_g, 4),
            "cr_fallback": round(cr_f, 4),
            "cr_divergence": round(cr_div, 4),
            "nsp_greedy": round(nsp_g, 4),
            "nsp_fallback": round(nsp_f, 4),
            "nsp_divergence": round(nsp_div, 4),
            "cer_sep_greedy": round(cer_g_sep, 6),
            "cer_sep_fallback": round(cer_f_sep, 6),
            "cer_sep_hybrid": round(min(cer_g_sep, cer_f_sep), 6),  # oracle hybrid
            "temp_fallback_used": _to_float(g.get("temp_sep1_used", 0)) > 0,
        })

    return _analyze_divergence_results(analyses, out_dir)


def run_hybrid_experiment(
    out_dir: Path, num_pairs: int = 5, quick: bool = False,
) -> dict[str, Any]:
    """Run the segment-level hybrid experiment with fresh ASR.

    This re-runs Whisper with greedy + fallback on a subset, producing
    transcript-level divergence analysis with actual text comparison.
    """
    import whisper

    out_dir.mkdir(parents=True, exist_ok=True)
    model = whisper.load_model("tiny")

    ratios = [0.0, 0.15, 0.35, 0.60, 0.90] if quick else [
        0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45,
        0.50, 0.60, 0.70, 0.80, 0.90,
    ]
    plans = select_pairs(num_pairs)
    print(f"[contrastive] model=tiny pairs={len(plans)} ratios={len(ratios)}", flush=True)

    fieldnames = [
        "pair_id", "con", "pro", "overlap_ratio",
        # CER values
        "cer_mixed_greedy", "cer_mixed_fallback", "cer_mixed_hybrid",
        "cer_sep_greedy", "cer_sep_fallback", "cer_sep_hybrid",
        # Divergence
        "div_mixed", "div_sep",
        # Signals
        "cr_mixed_greedy", "cr_mixed_fallback",
        "cr_sep_greedy", "cr_sep_fallback",
        # Temperature used
        "temp_mixed_used", "temp_sep_used",
    ]

    rows: list[dict[str, Any]] = []
    curve_path = out_dir / "contrastive_curve.csv"

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

                # Dual decode: greedy + fallback for mixed and separated
                mx_g = transcribe_with_signals(model, mixed, "greedy")
                mx_f = transcribe_with_signals(model, mixed, "fallback")
                s1_g = transcribe_with_signals(model, t1_trim, "greedy")
                s1_f = transcribe_with_signals(model, t1_trim, "fallback")
                s2_g = transcribe_with_signals(model, t2_trim, "greedy")
                s2_f = transcribe_with_signals(model, t2_trim, "fallback")

                sep_g = s1_g["text"] + s2_g["text"]
                sep_f = s1_f["text"] + s2_f["text"]

                # Divergence
                div_mixed = text_divergence(mx_g["text"], mx_f["text"])
                div_sep = text_divergence(sep_g, sep_f)

                # Hybrid: use fallback when divergent
                mx_hybrid = segment_hybrid(mx_g["text"], mx_f["text"])
                sep_hybrid = segment_hybrid(sep_g, sep_f)

                # CER
                cer_m_g = compute_cer(ref, mx_g["text"])["cer"]
                cer_m_f = compute_cer(ref, mx_f["text"])["cer"]
                cer_m_h = compute_cer(ref, mx_hybrid)["cer"]
                cer_s_g = compute_cer(ref, sep_g)["cer"]
                cer_s_f = compute_cer(ref, sep_f)["cer"]
                cer_s_h = compute_cer(ref, sep_hybrid)["cer"]

                row = {
                    "pair_id": pi, "con": plan.con_path.name, "pro": plan.pro_path.name,
                    "overlap_ratio": ratio,
                    "cer_mixed_greedy": round(cer_m_g, 6),
                    "cer_mixed_fallback": round(cer_m_f, 6),
                    "cer_mixed_hybrid": round(cer_m_h, 6),
                    "cer_sep_greedy": round(cer_s_g, 6),
                    "cer_sep_fallback": round(cer_s_f, 6),
                    "cer_sep_hybrid": round(cer_s_h, 6),
                    "div_mixed": round(div_mixed, 6),
                    "div_sep": round(div_sep, 6),
                    "cr_mixed_greedy": round(mx_g["max_compression_ratio"], 4),
                    "cr_mixed_fallback": round(mx_f["max_compression_ratio"], 4),
                    "cr_sep_greedy": round(max(s1_g["max_compression_ratio"], s2_g["max_compression_ratio"]), 4),
                    "cr_sep_fallback": round(max(s1_f["max_compression_ratio"], s2_f["max_compression_ratio"]), 4),
                    "temp_mixed_used": round(mx_f["max_temperature"], 3),
                    "temp_sep_used": round(max(s1_f["max_temperature"], s2_f["max_temperature"]), 3),
                }
                writer.writerow(row)
                rows.append(row)

            fh.flush()
            print(f"[contrastive] pair {pi + 1}/{len(plans)} done", flush=True)

    summary = analyze_hybrid_results(rows, out_dir)
    print(f"[contrastive] n={len(rows)} wrote {OUT_DIR.relative_to(PROJECT_ROOT)}", flush=True)
    return summary


def analyze_hybrid_results(rows: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    """Analyze the hybrid experiment results."""

    def _mean(xs: list[float]) -> float:
        vals = [x for x in xs if x == x]
        return round(sum(vals) / len(vals), 6) if vals else 0.0

    # RQ1: Does divergence predict CER?
    divergent_rows = [r for r in rows if float(r["div_sep"]) > 0.1]
    agreeing_rows = [r for r in rows if float(r["div_sep"]) <= 0.1]

    mean_cer_divergent = _mean([float(r["cer_sep_greedy"]) for r in divergent_rows]) if divergent_rows else 0.0
    mean_cer_agreeing = _mean([float(r["cer_sep_greedy"]) for r in agreeing_rows]) if agreeing_rows else 0.0

    # RQ2: Hybrid vs greedy
    cer_greedy = [float(r["cer_sep_greedy"]) for r in rows]
    cer_fallback = [float(r["cer_sep_fallback"]) for r in rows]
    cer_hybrid = [float(r["cer_sep_hybrid"]) for r in rows]

    # RQ3: Divergence rate by overlap
    ratios = sorted({float(r["overlap_ratio"]) for r in rows})
    per_ratio = []
    for ratio in ratios:
        at = [r for r in rows if float(r["overlap_ratio"]) == ratio]
        div_rate = sum(1 for r in at if float(r["div_sep"]) > 0.1) / len(at) if at else 0
        per_ratio.append({
            "overlap_ratio": ratio,
            "mean_cer_greedy": _mean([float(r["cer_sep_greedy"]) for r in at]),
            "mean_cer_fallback": _mean([float(r["cer_sep_fallback"]) for r in at]),
            "mean_cer_hybrid": _mean([float(r["cer_sep_hybrid"]) for r in at]),
            "divergence_rate": round(div_rate, 4),
            "mean_divergence": _mean([float(r["div_sep"]) for r in at]),
        })

    # Divergence AUC
    div_scores = [float(r["div_sep"]) for r in rows]
    cers = [float(r["cer_sep_greedy"]) for r in rows]
    div_auc_05 = rank_auc(div_scores, [1 if c > 0.5 else 0 for c in cers])
    div_auc_10 = rank_auc(div_scores, [1 if c > 1.0 else 0 for c in cers])

    result = {
        "n": len(rows),
        "n_divergent": len(divergent_rows),
        "n_agreeing": len(agreeing_rows),
        "rq1_divergence_predicts_cer": {
            "mean_cer_divergent_sep": mean_cer_divergent,
            "mean_cer_agreeing_sep": mean_cer_agreeing,
            "divergent_is_worse": mean_cer_divergent > mean_cer_agreeing,
            "auc_divergence_cer>0.5": round(div_auc_05, 4),
            "auc_divergence_cer>1.0": round(div_auc_10, 4),
        },
        "rq2_hybrid_vs_greedy": {
            "mean_cer_greedy": _mean(cer_greedy),
            "mean_cer_fallback": _mean(cer_fallback),
            "mean_cer_hybrid": _mean(cer_hybrid),
            "hybrid_improvement_over_greedy": round(_mean(cer_greedy) - _mean(cer_hybrid), 6),
            "n_hybrid_helped": sum(1 for g, h in zip(cer_greedy, cer_hybrid) if h < g),
            "n_hybrid_hurt": sum(1 for g, h in zip(cer_greedy, cer_hybrid) if h > g),
        },
        "rq3_per_ratio": per_ratio,
    }

    # Write outputs
    (out_dir / "contrastive_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_per_ratio_csv(per_ratio, out_dir / "divergence_by_ratio.csv")

    try:
        render_figure(per_ratio, result, out_dir)
    except Exception as exc:
        print(f"[contrastive] figure skipped: {exc}", flush=True)

    return result


def _analyze_divergence_results(
    analyses: list[dict[str, Any]], out_dir: Path,
) -> dict[str, Any]:
    """Analyze signal-level divergence from existing phase_curve data."""

    def _mean(xs: list[float]) -> float:
        vals = [x for x in xs if x == x]
        return round(sum(vals) / len(vals), 6) if vals else 0.0

    # Does CR divergence predict CER?
    cr_divs = [a["cr_divergence"] for a in analyses]
    cers = [a["cer_sep_greedy"] for a in analyses]
    spearman_cr_div = spearman_corr(cr_divs, cers)

    # Per-overlap-ratio analysis
    ratios = sorted({a["overlap_ratio"] for a in analyses})
    per_ratio = []
    for ratio in ratios:
        at = [a for a in analyses if a["overlap_ratio"] == ratio]
        per_ratio.append({
            "overlap_ratio": ratio,
            "mean_cr_greedy": _mean([a["cr_greedy"] for a in at]),
            "mean_cr_fallback": _mean([a["cr_fallback"] for a in at]),
            "mean_cr_divergence": _mean([a["cr_divergence"] for a in at]),
            "mean_cer_greedy": _mean([a["cer_sep_greedy"] for a in at]),
            "mean_cer_fallback": _mean([a["cer_sep_fallback"] for a in at]),
            "temp_fallback_fired_frac": sum(1 for a in at if a["temp_fallback_used"]) / len(at) if at else 0,
        })

    result = {
        "n": len(analyses),
        "source": "existing phase_curve.csv (no new ASR)",
        "signal_divergence": {
            "spearman_cr_divergence_vs_cer": spearman_cr_div,
        },
        "per_ratio": per_ratio,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "signal_divergence_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_per_ratio_csv(per_ratio, out_dir / "signal_divergence_by_ratio.csv")
    return result


def _write_per_ratio_csv(per_ratio: list[dict[str, Any]], path: Path) -> None:
    if not per_ratio:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(per_ratio[0].keys()))
        writer.writeheader()
        writer.writerows(per_ratio)


def render_figure(
    per_ratio: list[dict[str, Any]], summary: dict[str, Any], out_dir: Path,
) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    ratios = [r["overlap_ratio"] for r in per_ratio]
    cer_g = [r["mean_cer_greedy"] for r in per_ratio]
    cer_f = [r["mean_cer_fallback"] for r in per_ratio]
    cer_h = [r["mean_cer_hybrid"] for r in per_ratio]
    div_rate = [r["divergence_rate"] for r in per_ratio]

    ax1.plot(ratios, cer_g, "-o", color="#e45756", label="greedy")
    ax1.plot(ratios, cer_f, "-s", color="#4c78a8", label="fallback")
    ax1.plot(ratios, cer_h, "-^", color="#54a24b", label="hybrid")
    ax1.set_xlabel("overlap ratio")
    ax1.set_ylabel("CER (separated)")
    ax1.set_title("Greedy vs Fallback vs Hybrid CER")
    ax1.legend()
    ax1.grid(alpha=0.3)

    ax2.bar(ratios, div_rate, width=0.06, color="#f58518", alpha=0.7)
    ax2.set_xlabel("overlap ratio")
    ax2.set_ylabel("Divergence rate (frac with div > 0.1)")
    ax2.set_title("Greedy-Fallback Divergence Rate")
    ax2.grid(alpha=0.3)

    rq2 = summary.get("rq2_hybrid_vs_greedy", {})
    fig.suptitle(
        f"Contrastive Decoding | Hybrid improvement: {rq2.get('hybrid_improvement_over_greedy', '?')}",
        fontsize=10,
    )
    fig.tight_layout()
    fig_path = out_dir / "contrastive_analysis.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    return fig_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Contrastive Decoding (frontier).")
    parser.add_argument("--pairs", type=int, default=5, help="Number of speaker pairs.")
    parser.add_argument("--quick", action="store_true", help="Coarse ratio grid.")
    parser.add_argument("--signal-only", action="store_true",
                        help="Analyze existing phase_curve only (no new ASR).")
    parser.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    if args.signal_only:
        analyze_existing_phase_curve(out_dir)
    else:
        run_hybrid_experiment(out_dir, num_pairs=args.pairs, quick=args.quick)


if __name__ == "__main__":
    main()
