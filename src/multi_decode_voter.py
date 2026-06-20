"""Multi-Decode Self-Consistency Voter -- experimental/frontier.

Research question (pre-registered, Issue #858):
  Every existing reference-free signal (compression_ratio, no_speech_prob,
  repetition, avg_logprob) comes from a SINGLE decode pass.  This module asks
  whether STABILITY across multiple decoding passes — the same audio decoded at
  different temperatures — produces a stronger reference-free quality signal.

  RQ1 (signal quality): Does inter-decode agreement (pairwise CER among N
     temperature-varied decodes) correlate with transcript quality (CER vs
     reference) better than compression_ratio?
  RQ2 (hallucination instability): Do hallucinated segments show high
     inter-decode variance while clean segments are stable?
  RQ3 (voting): Does character-level majority voting across N decodes reduce
     CER compared to any single greedy decode?

  Hypotheses:
    H1: Spearman(agreement, true_CER) > Spearman(compression_ratio, true_CER).
    H2: Segments where inter-decode CER > 0.3 are predominantly hallucinated.
    H3: Majority-vote CER < greedy CER on high-overlap (hallucination-prone) samples.

  Labels: experimental/frontier. References are synthetic/silver (Whisper-small
  on clean snippets). ASR = Whisper-tiny. CER is post-hoc evaluation only.
  Stable tables untouched; outputs go to results/frontier/multi_decode_voter/.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT
from .evaluate_cer import compute_cer, repetition_count_from_text
from .generate_synthetic_overlap import build_mixture, read_mono_audio
from .reference_free_qe import rank_auc, spearman_corr
from .separation_tax_phase import (
    WHISPER_CONFIGS,
    load_snippet_reference,
    select_pairs,
    trim_silence,
)

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "multi_decode_voter"

# Temperatures to probe.  0.0 = greedy (deterministic).  Others introduce
# stochasticity — if the decode is "real", small perturbations shouldn't
# change it; if it's a hallucination, it will flip between random completions.
TEMPERATURES = [0.0, 0.1, 0.2, 0.3, 0.4]


# ---- Pure agreement / voting logic (unit-testable, no I/O) -----------------------

def character_majority_vote(texts: list[str]) -> str:
    """Fuse N transcripts by character-level majority voting at each position.

    Aligns by index (shortest-text-length).  For each position, the character
    that appears in the most texts wins.  Ties broken by first occurrence.
    Returns the fused text truncated to the shortest input length.
    """
    if not texts:
        return ""
    if len(texts) == 1:
        return texts[0]

    min_len = min(len(t) for t in texts)
    if min_len == 0:
        # Return the longest text (most informative)
        return max(texts, key=len)

    result = []
    for pos in range(min_len):
        chars = [t[pos] for t in texts]
        counts = Counter(chars)
        # Most common char, tie-break by first occurrence
        best_char = max(chars, key=lambda c: (counts[c], -chars.index(c)))
        result.append(best_char)
    return "".join(result)


def decode_agreement(texts: list[str]) -> dict[str, float]:
    """Compute agreement metrics across multiple decodes.

    Returns:
        mean_pairwise_cer: average CER between all pairs (lower = more agreement)
        min_pairwise_cer: minimum pair CER (best agreement)
        max_pairwise_cer: maximum pair CER (worst agreement)
        agreement_score: 1/(1 + mean_pairwise_cer * 10) mapped to [0,1]
        length_cv: coefficient of variation of text lengths
    """
    if len(texts) < 2:
        return {
            "mean_pairwise_cer": 0.0,
            "min_pairwise_cer": 0.0,
            "max_pairwise_cer": 0.0,
            "agreement_score": 1.0,
            "length_cv": 0.0,
        }

    pairwise_cers = []
    for i, t1 in enumerate(texts):
        for t2 in texts[i + 1:]:
            pairwise_cers.append(compute_cer(t1, t2)["cer"])

    lengths = [len(t) for t in texts]
    mean_len = sum(lengths) / len(lengths)
    length_cv = (
        (sum((l - mean_len) ** 2 for l in lengths) / len(lengths)) ** 0.5 / mean_len
        if mean_len > 0
        else 0.0
    )

    mean_cer = sum(pairwise_cers) / len(pairwise_cers)
    return {
        "mean_pairwise_cer": round(mean_cer, 6),
        "min_pairwise_cer": round(min(pairwise_cers), 6),
        "max_pairwise_cer": round(max(pairwise_cers), 6),
        "agreement_score": round(1.0 / (1.0 + mean_cer * 10), 6),
        "length_cv": round(length_cv, 6),
    }


def route_by_stability(
    agreement: dict[str, float],
    allowed: list[str] | None = None,
) -> str:
    """Pick the arm with highest agreement (lowest inter-decode variance)."""
    if allowed is None:
        allowed = list(agreement.keys())
    if not allowed:
        return ""
    best = max(allowed, key=lambda a: agreement.get(a, -1.0))
    return best


# ---- Whisper driver (requires model) --------------------------------------------

def decode_multi_temperature(
    model: Any,
    audio: np.ndarray,
    temperatures: list[float] | None = None,
    language: str = "zh",
) -> dict[float, dict[str, Any]]:
    """Decode the same audio at multiple temperatures.  Returns per-temp results."""
    if temperatures is None:
        temperatures = TEMPERATURES

    audio = np.ascontiguousarray(np.asarray(audio, dtype=np.float32))
    results = {}
    for temp in temperatures:
        cfg = {
            "temperature": temp,
            "condition_on_previous_text": False,
        }
        t0 = time.perf_counter()
        out = model.transcribe(audio, language=language, verbose=False, fp16=False, **cfg)
        runtime = time.perf_counter() - t0
        segs = out.get("segments", [])
        text = str(out.get("text", "")).strip()
        results[temp] = {
            "text": text,
            "n_segments": len(segs),
            "runtime_sec": round(runtime, 3),
            "max_cr": float(max((s.get("compression_ratio", 0.0) for s in segs), default=0.0)),
            "max_nsp": float(max((s.get("no_speech_prob", 0.0) for s in segs), default=0.0)),
            "mean_logprob": float(
                np.mean([s.get("avg_logprob", 0.0) for s in segs])
            ) if segs else 0.0,
        }
    return results


# ---- Main driver -----------------------------------------------------------------

def run(out_dir: Path, num_pairs: int = 5, quick: bool = False) -> dict[str, Any]:
    """Run the multi-decode voting experiment on the synthetic grid."""
    import whisper

    out_dir.mkdir(parents=True, exist_ok=True)
    model = whisper.load_model("tiny")

    ratios = [0.0, 0.15, 0.35, 0.60, 0.90] if quick else [
        0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45,
        0.50, 0.60, 0.70, 0.80, 0.90,
    ]
    plans = select_pairs(num_pairs)
    print(f"[multi-decode] model=tiny pairs={len(plans)} ratios={len(ratios)} "
          f"temps={TEMPERATURES}", flush=True)

    fieldnames = [
        "pair_id", "con", "pro", "overlap_ratio",
        # CER of individual decodes
        "cer_mixed_greedy", "cer_sep_greedy",
        "cer_mixed_vote", "cer_sep_vote",
        # Agreement metrics per arm
        "agr_mixed_mean_cer", "agr_mixed_score", "agr_mixed_cv",
        "agr_sep_mean_cer", "agr_sep_score", "agr_sep_cv",
        # Compression ratio baseline
        "cr_mixed_greedy", "cr_sep_greedy",
        # Per-temp CER for mixed
    ] + [f"cer_mixed_t{t}" for t in TEMPERATURES] + [
        f"cer_sep_t{t}" for t in TEMPERATURES
    ]

    rows: list[dict[str, Any]] = []
    curve_path = out_dir / "decode_curve.csv"

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

                # Multi-temperature decode: mixed and separated
                mixed_results = decode_multi_temperature(model, mixed, TEMPERATURES)
                sep1_results = decode_multi_temperature(model, t1_trim, TEMPERATURES)
                sep2_results = decode_multi_temperature(model, t2_trim, TEMPERATURES)

                # Build per-temp texts
                mixed_texts = {t: mixed_results[t]["text"] for t in TEMPERATURES}
                sep_texts = {
                    t: sep1_results[t]["text"] + sep2_results[t]["text"]
                    for t in TEMPERATURES
                }

                # CER of greedy (temp=0.0) — the baseline
                cer_mixed_greedy = compute_cer(ref, mixed_texts[0.0])["cer"]
                cer_sep_greedy = compute_cer(ref, sep_texts[0.0])["cer"]

                # CER of majority vote
                vote_mixed = character_majority_vote(list(mixed_texts.values()))
                vote_sep = character_majority_vote(list(sep_texts.values()))
                cer_mixed_vote = compute_cer(ref, vote_mixed)["cer"]
                cer_sep_vote = compute_cer(ref, vote_sep)["cer"]

                # Agreement metrics
                agr_mixed = decode_agreement(list(mixed_texts.values()))
                agr_sep = decode_agreement(list(sep_texts.values()))

                # Compression ratio (from greedy decode)
                cr_mixed = mixed_results[0.0]["max_cr"]
                cr_sep = max(sep1_results[0.0]["max_cr"], sep2_results[0.0]["max_cr"])

                row: dict[str, Any] = {
                    "pair_id": pi,
                    "con": plan.con_path.name,
                    "pro": plan.pro_path.name,
                    "overlap_ratio": ratio,
                    "cer_mixed_greedy": round(cer_mixed_greedy, 6),
                    "cer_sep_greedy": round(cer_sep_greedy, 6),
                    "cer_mixed_vote": round(cer_mixed_vote, 6),
                    "cer_sep_vote": round(cer_sep_vote, 6),
                    "agr_mixed_mean_cer": agr_mixed["mean_pairwise_cer"],
                    "agr_mixed_score": agr_mixed["agreement_score"],
                    "agr_mixed_cv": agr_mixed["length_cv"],
                    "agr_sep_mean_cer": agr_sep["mean_pairwise_cer"],
                    "agr_sep_score": agr_sep["agreement_score"],
                    "agr_sep_cv": agr_sep["length_cv"],
                    "cr_mixed_greedy": round(cr_mixed, 4),
                    "cr_sep_greedy": round(cr_sep, 4),
                }
                for t in TEMPERATURES:
                    row[f"cer_mixed_t{t}"] = round(compute_cer(ref, mixed_texts[t])["cer"], 6)
                    row[f"cer_sep_t{t}"] = round(compute_cer(ref, sep_texts[t])["cer"], 6)

                writer.writerow(row)
                rows.append(row)

            fh.flush()
            print(f"[multi-decode] pair {pi + 1}/{len(plans)} done", flush=True)

    summary = analyze(rows, out_dir)
    print(f"[multi-decode] n={len(rows)} wrote {OUT_DIR.relative_to(PROJECT_ROOT)}", flush=True)
    return summary


def analyze(rows: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    """Analyze multi-decode voting results."""

    def _mean(xs: list[float]) -> float:
        vals = [x for x in xs if x == x]
        return round(sum(vals) / len(vals), 6) if vals else 0.0

    # RQ1: Signal quality — agreement vs compression_ratio
    # Use the arm (mixed or sep) that is oracle-better per row
    agreement_scores = []
    cr_scores = []
    oracle_cers = []
    greedy_cers = []
    vote_cers = []

    for r in rows:
        m_greedy = float(r["cer_mixed_greedy"])
        s_greedy = float(r["cer_sep_greedy"])
        m_vote = float(r["cer_mixed_vote"])
        s_vote = float(r["cer_sep_vote"])

        oracle_cer = min(m_greedy, s_greedy)
        oracle_cers.append(oracle_cer)

        # Use the oracle-better arm's signals
        if m_greedy <= s_greedy:
            agreement_scores.append(float(r["agr_mixed_score"]))
            cr_scores.append(1.0 / (1.0 + float(r["cr_mixed_greedy"])))
            greedy_cers.append(m_greedy)
            vote_cers.append(m_vote)
        else:
            agreement_scores.append(float(r["agr_sep_score"]))
            cr_scores.append(1.0 / (1.0 + float(r["cr_sep_greedy"])))
            greedy_cers.append(s_greedy)
            vote_cers.append(s_vote)

    # Spearman correlations
    spearman_agr = spearman_corr(agreement_scores, oracle_cers)
    spearman_cr = spearman_corr(cr_scores, oracle_cers)

    # Note: agreement_score is higher = more agreement = better quality
    # So we expect NEGATIVE correlation with CER (high agreement → low CER)
    # But cr_score is higher = lower CR = better quality
    # For fair comparison, use |Spearman| (magnitude of correlation)
    # Actually: agreement_score = 1/(1 + mean_cer*10), so higher = more agreement
    # We want: higher agreement → lower CER → NEGATIVE Spearman
    # For CR: higher cr_score → lower CR → should also correlate NEGATIVELY with CER

    # Detection AUC: does agreement predict CER > threshold?
    agr_auc_05 = rank_auc(
        [-s for s in agreement_scores],  # negate so higher = worse (like CR)
        [1 if c > 0.5 else 0 for c in oracle_cers],
    )
    cr_auc_05 = rank_auc(
        [-s for s in cr_scores],
        [1 if c > 0.5 else 0 for c in oracle_cers],
    )

    # RQ3: Voting benefit
    mean_greedy = _mean(greedy_cers)
    mean_vote = _mean(vote_cers)
    vote_helped = sum(1 for g, v in zip(greedy_cers, vote_cers) if v < g)
    vote_hurt = sum(1 for g, v in zip(greedy_cers, vote_cers) if v > g)

    # Per-overlap analysis
    ratios = sorted({float(r["overlap_ratio"]) for r in rows})
    per_ratio = []
    for ratio in ratios:
        at = [r for r in rows if float(r["overlap_ratio"]) == ratio]
        m_sep_g = _mean([float(r["cer_sep_greedy"]) for r in at])
        m_sep_v = _mean([float(r["cer_sep_vote"]) for r in at])
        m_agr = _mean([float(r["agr_sep_score"]) for r in at])
        per_ratio.append({
            "overlap_ratio": ratio,
            "mean_cer_sep_greedy": m_sep_g,
            "mean_cer_sep_vote": m_sep_v,
            "mean_agreement_sep": m_agr,
            "vote_delta": round(m_sep_g - m_sep_v, 6),
        })

    result = {
        "n": len(rows),
        "temperatures": TEMPERATURES,
        "signal_comparison": {
            "spearman_agreement_vs_cer": spearman_agr,
            "spearman_cr_vs_cer": spearman_cr,
            "agreement_wins": abs(spearman_agr) > abs(spearman_cr),
            "auc_agreement_cer>0.5": round(agr_auc_05, 4),
            "auc_cr_cer>0.5": round(cr_auc_05, 4),
        },
        "voting": {
            "mean_greedy_cer": mean_greedy,
            "mean_vote_cer": mean_vote,
            "vote_improvement": round(mean_greedy - mean_vote, 6),
            "n_vote_helped": vote_helped,
            "n_vote_hurt": vote_hurt,
            "n_total": len(greedy_cers),
        },
        "per_ratio": per_ratio,
    }

    # Write outputs
    (out_dir / "voting_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_per_ratio_csv(per_ratio, out_dir / "vote_by_ratio.csv")

    try:
        render_figure(per_ratio, result, out_dir)
    except Exception as exc:
        print(f"[multi-decode] figure skipped: {exc}", flush=True)

    return result


def _write_per_ratio_csv(per_ratio: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(per_ratio[0].keys()) if per_ratio else [])
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
    cer_greedy = [r["mean_cer_sep_greedy"] for r in per_ratio]
    cer_vote = [r["mean_cer_sep_vote"] for r in per_ratio]
    agr = [r["mean_agreement_sep"] for r in per_ratio]

    ax1.plot(ratios, cer_greedy, "-o", color="#e45756", label="greedy (temp=0.0)")
    ax1.plot(ratios, cer_vote, "-s", color="#4c78a8", label="majority vote")
    ax1.fill_between(ratios, cer_greedy, cer_vote, alpha=0.15,
                     color="#4c78a8", where=[v < g for g, v in zip(cer_greedy, cer_vote)])
    ax1.set_xlabel("overlap ratio")
    ax1.set_ylabel("CER (separated arm)")
    ax1.set_title("Greedy vs Majority-Vote CER")
    ax1.legend()
    ax1.grid(alpha=0.3)

    ax2.plot(ratios, agr, "-^", color="#54a24b", label="agreement score")
    ax2_twin = ax2.twinx()
    ax2_twin.plot(ratios, cer_greedy, "--", color="#e45756", alpha=0.5, label="CER (greedy)")
    ax2.set_xlabel("overlap ratio")
    ax2.set_ylabel("Agreement Score (higher = more stable)")
    ax2_twin.set_ylabel("CER", color="#e45756")
    ax2.set_title("Decode Stability vs Quality")
    ax2.legend(loc="upper left")
    ax2_twin.legend(loc="upper right")
    ax2.grid(alpha=0.3)

    sig = summary.get("signal_comparison", {})
    fig.suptitle(
        f"Multi-Decode Voting | Spearman(agreement,CER)={sig.get('spearman_agreement_vs_cer', '?'):.3f} "
        f"vs CR={sig.get('spearman_cr_vs_cer', '?'):.3f}",
        fontsize=10,
    )
    fig.tight_layout()
    fig_path = out_dir / "multi_decode_analysis.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    return fig_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-Decode Self-Consistency Voter (frontier).")
    parser.add_argument("--pairs", type=int, default=5, help="Number of speaker pairs.")
    parser.add_argument("--quick", action="store_true", help="Coarse 5-point ratio grid.")
    parser.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(Path(args.out_dir), num_pairs=args.pairs, quick=args.quick)


if __name__ == "__main__":
    main()
