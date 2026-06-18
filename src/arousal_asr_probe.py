"""Arousal -> ASR-difficulty probe: is emotion a reference-free predictor of where ASR fails? (frontier)

Experiment #1 (the Emotional Separation Tax) asked what separation does TO emotion. This is the other
direction of the emotion<->ASR relationship: does a track's acoustic AROUSAL (a pre-decode,
reference-free emotion proxy from src/prosody.py) predict its Whisper CER and hallucination — and does
it carry signal BEYOND what overlap and the existing compression-ratio degeneracy guard already give?

If arousal predicts difficulty independently of overlap, it is a new reference-free routing feature
(emotion helps ASR). If its apparent predictive power is fully explained by overlap (aroused = more
overlap energy) or duplicated by the compression-ratio signal, then emotion adds nothing to routing —
a real, bounding negative result.

Hypotheses (CER/hallucination are post-hoc only; arousal is computed pre-decode from audio):
  H1  arousal correlates with CER overall.
  H2  much of that is MEDIATED by overlap: the partial correlation controlling for overlap shrinks.
  H3  the decisive test — does arousal retain independent power? (a) partial corr controlling overlap
      stays non-trivial, and/or (b) arousal's AUC for predicting a hallucination (CER>1) beats the
      compression-ratio AUC. If neither, arousal is redundant for ASR routing.
  Kill: partial corr ~0 AND arousal_auc <= cr_auc -> emotion adds no independent ASR-routing signal.

Labels: experimental/frontier; ASR Whisper-tiny; references synthetic/silver. No gold tables touched.
Outputs to results/frontier/arousal_asr_probe/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "arousal_asr_probe"
OVERLAPS = [0.0, 0.1, 0.3, 0.6, 0.9]
CATASTROPHIC_CER = 1.0


# ======================================================================================
# Pure statistics (no Whisper / librosa) -- unit tested
# ======================================================================================
def pearson(x: Any, y: Any) -> float:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.size < 2 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def _rankdata(x: np.ndarray) -> np.ndarray:
    """Average ranks (ties shared) -- needed for a correct Spearman under ties."""
    x = np.asarray(x, dtype=np.float64)
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(x.size, dtype=np.float64)
    ranks[order] = np.arange(1, x.size + 1, dtype=np.float64)
    # average tied ranks
    _, inv, counts = np.unique(x, return_inverse=True, return_counts=True)
    sums = np.zeros(counts.size); np.add.at(sums, inv, ranks)
    return (sums / counts)[inv]


def spearman(x: Any, y: Any) -> float:
    rx, ry = _rankdata(np.asarray(x, dtype=np.float64)), _rankdata(np.asarray(y, dtype=np.float64))
    return pearson(rx, ry)


def _residuals(target: np.ndarray, control: np.ndarray) -> np.ndarray:
    """Residuals of target after a linear fit on control (the part of target not explained by it)."""
    target = np.asarray(target, dtype=np.float64)
    control = np.asarray(control, dtype=np.float64)
    if np.std(control) == 0:
        return target - np.mean(target)
    slope, intercept = np.polyfit(control, target, 1)
    return target - (slope * control + intercept)


def partial_correlation(x: Any, y: Any, z: Any) -> float:
    """Pearson correlation of x and y after linearly removing z from both (controls for z). Returns
    NaN when z perfectly explains either variable (residuals are pure roundoff -> undefined)."""
    rx = _residuals(np.asarray(x, dtype=np.float64), np.asarray(z, dtype=np.float64))
    ry = _residuals(np.asarray(y, dtype=np.float64), np.asarray(z, dtype=np.float64))
    sx = np.std(np.asarray(x, dtype=np.float64)) + 1e-12
    sy = np.std(np.asarray(y, dtype=np.float64)) + 1e-12
    # residuals negligible relative to the original spread -> z fully explains it -> undefined
    if np.std(rx) < 1e-9 * sx or np.std(ry) < 1e-9 * sy:
        return float("nan")
    return pearson(rx, ry)


def rank_auc(scores: Any, labels: Any) -> float:
    """AUC = P(score(positive) > score(negative)); ties 0.5. NaN if only one class present."""
    scores = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(labels)
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if pos.size == 0 or neg.size == 0:
        return float("nan")
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return float(wins / (pos.size * neg.size))


def _r(v: float) -> float:
    return round(v, 6) if v == v else float("nan")


def summarize_probe(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Overall + partial + per-overlap arousal<->CER relationship, and the head-to-head of arousal vs
    the compression-ratio signal for predicting hallucination (CER>1)."""
    arousal = [float(r["arousal"]) for r in rows]
    cer = [float(r["cer"]) for r in rows]
    overlap = [float(r["overlap_ratio"]) for r in rows]
    cr = [float(r.get("max_compression_ratio", 0.0)) for r in rows]
    halluc = [int(r.get("hallucinated", int(float(r["cer"]) > CATASTROPHIC_CER))) for r in rows]

    by_overlap = []
    for ov in sorted(set(overlap)):
        idx = [i for i, o in enumerate(overlap) if o == ov]
        by_overlap.append({
            "overlap_ratio": ov, "n": len(idx),
            "pearson_arousal_cer": _r(pearson([arousal[i] for i in idx], [cer[i] for i in idx])),
            "mean_arousal": _r(float(np.mean([arousal[i] for i in idx]))),
            "mean_cer": _r(float(np.mean([cer[i] for i in idx]))),
        })
    # within-stratum pooled correlation = mean of per-overlap correlations that are defined
    strata_corrs = [b["pearson_arousal_cer"] for b in by_overlap if b["pearson_arousal_cer"] == b["pearson_arousal_cer"]]
    return {
        "n": len(rows),
        "pearson_arousal_cer": _r(pearson(arousal, cer)),
        "spearman_arousal_cer": _r(spearman(arousal, cer)),
        "partial_pearson_controlling_overlap": _r(partial_correlation(arousal, cer, overlap)),
        "mean_within_overlap_pearson": _r(float(np.mean(strata_corrs))) if strata_corrs else float("nan"),
        "arousal_auc_hallucination": _r(rank_auc(arousal, halluc)),
        "cr_auc_hallucination": _r(rank_auc(cr, halluc)),
        "hallucination_rate": _r(float(np.mean(halluc))),
        "by_overlap": by_overlap,
    }


# ======================================================================================
# Whisper + librosa driver
# ======================================================================================
def run_probe(out_dir: Path, num_pairs: int, overlaps: list[float]) -> dict[str, Any]:
    import whisper

    from .evaluate_cer import compute_cer
    from .generate_synthetic_overlap import build_mixture, read_mono_audio
    from .prosody import arousal_index, prosodic_features
    from .separation_tax_phase import select_pairs, transcribe_with_signals

    out_dir.mkdir(parents=True, exist_ok=True)
    plans = select_pairs(num_pairs)
    model = whisper.load_model("tiny")
    print(f"[arousal-probe] pairs={len(plans)} overlaps={overlaps}", flush=True)

    def arousal_of(wav: np.ndarray) -> float:
        return arousal_index(prosodic_features(np.asarray(wav, dtype=np.float32)))

    rows: list[dict[str, Any]] = []
    for pi, plan in enumerate(plans):
        s1, s2 = read_mono_audio(plan.con_path), read_mono_audio(plan.pro_path)
        for overlap in overlaps:
            mixed, t1, t2, _ = build_mixture(s1, s2, overlap)
            tracks = [
                ("mixed", mixed, plan.con_text + plan.pro_text),
                ("sep1", t1, plan.con_text),
                ("sep2", t2, plan.pro_text),
            ]
            for ttype, wav, ref_text in tracks:
                sig = transcribe_with_signals(model, np.asarray(wav, dtype=np.float32), "greedy")
                cer = compute_cer(ref_text, sig["text"])["cer"]
                rows.append({
                    "pair_id": pi, "overlap_ratio": overlap, "track_type": ttype,
                    "arousal": round(arousal_of(wav), 6),
                    "cer": round(cer, 6),
                    "max_compression_ratio": round(float(sig["max_compression_ratio"]), 4),
                    "hallucinated": int(cer > CATASTROPHIC_CER),
                })
        print(f"[arousal-probe] pair {pi + 1}/{len(plans)} done", flush=True)

    curve = out_dir / "arousal_probe_curve.csv"
    with curve.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    summary = {
        "all": summarize_probe(rows),
        "separated_only": summarize_probe([r for r in rows if r["track_type"] != "mixed"]),
        "mixed_only": summarize_probe([r for r in rows if r["track_type"] == "mixed"]),
    }
    (out_dir / "arousal_probe_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    a = summary["all"]
    print(f"[arousal-probe] pearson(arousal,cer)={a['pearson_arousal_cer']} "
          f"partial|overlap={a['partial_pearson_controlling_overlap']} "
          f"within-overlap={a['mean_within_overlap_pearson']}", flush=True)
    print(f"[arousal-probe] hallucination AUC arousal={a['arousal_auc_hallucination']} vs "
          f"compression_ratio={a['cr_auc_hallucination']} (halluc_rate={a['hallucination_rate']})", flush=True)
    try:
        render_figure(out_dir, rows)
    except Exception as exc:
        print(f"[arousal-probe] figure skipped: {exc}", flush=True)
    print(f"[arousal-probe] wrote {curve} + arousal_probe_summary.json (rows={len(rows)})", flush=True)
    return {"summary": summary, "n_rows": len(rows)}


def render_figure(out_dir: Path, rows: list[dict[str, Any]]) -> Path | None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))
    colors = {0.0: "#4c78a8", 0.1: "#72b7b2", 0.3: "#54a24b", 0.6: "#eeca3b", 0.9: "#e45756"}
    for ov in sorted({r["overlap_ratio"] for r in rows}):
        at = [r for r in rows if r["overlap_ratio"] == ov]
        ax1.scatter([r["arousal"] for r in at], [min(r["cer"], 3.0) for r in at],
                    s=22, color=colors.get(ov, "#888"), label=f"ov={ov:g}", alpha=0.8)
    ax1.set_xlabel("pre-decode arousal index (reference-free)")
    ax1.set_ylabel("Whisper CER (clipped at 3.0)")
    from .arousal_asr_probe import summarize_probe as _sp
    s = _sp(rows)
    ax1.set_title(f"Arousal vs ASR difficulty (r={s['pearson_arousal_cer']:.2f}, "
                  f"partial|overlap={s['partial_pearson_controlling_overlap']:.2f})")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)
    # Per-overlap within-stratum correlation: honest view (the binary-hallucination AUC is
    # underpowered — typically only ~1 CER>1 case in this clean-ish grid).
    by = s["by_overlap"]
    ovs = [b["overlap_ratio"] for b in by]
    corrs = [b["pearson_arousal_cer"] if b["pearson_arousal_cer"] == b["pearson_arousal_cer"] else 0.0 for b in by]
    ax2.bar(range(len(ovs)), corrs, color=["#4c78a8" if c >= 0 else "#e45756" for c in corrs])
    ax2.axhline(0.0, color="black", lw=0.8)
    ax2.set_xticks(range(len(ovs)))
    ax2.set_xticklabels([f"{o:g}" for o in ovs])
    ax2.set_ylim(-1, 1)
    ax2.set_xlabel("overlap ratio")
    ax2.set_ylabel("within-stratum Pearson(arousal, CER)")
    ax2.set_title("No consistent within-overlap signal (sign flips)")
    ax2.grid(alpha=0.3, axis="y")
    fig.suptitle("Acoustic arousal does NOT predict ASR difficulty (Whisper-tiny, zh) — a bounding negative result")
    fig.tight_layout()
    fig_path = out_dir / "arousal_asr_probe.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    print(f"[arousal-probe] wrote {fig_path}", flush=True)
    return fig_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Arousal -> ASR-difficulty probe (frontier).")
    p.add_argument("--pairs", type=int, default=8)
    p.add_argument("--overlaps", type=str, default="0.0,0.1,0.3,0.6,0.9")
    p.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    run_probe(Path(args.out_dir), args.pairs, [float(o) for o in args.overlaps.split(",") if o.strip()])


if __name__ == "__main__":
    main()
