"""Reference-free emotion-fidelity / separation-quality meter (experimental/frontier).

Findings #14 and #18 measured emotion preservation and built objective-aware routing using the CLEAN
SOURCE's prosody as the reference — an oracle unavailable at deploy time. This module removes that
crutch: it estimates, with NO clean reference and NO labels, how well a separated track preserved its
speaker's emotion, from the track's own internal SELF-CONSISTENCY:

  - speaker-embedding consistency: a clean single-speaker track has windows that all embed near one
    point (resemblyzer GE2E); cross-talk leakage drags some windows toward the other speaker, lowering
    the mean cosine to the track centroid.
  - prosodic coherence: a clean track has coherent per-window arousal; contamination injects foreign
    prosody, raising variance.

The two combine into a [0,1] fidelity meter. We then VALIDATE (analysis-only, using the oracle clean
reference we will not have at deploy) that the meter anti-correlates with the true emotion distortion
and with the cross-talk leakage alpha — i.e. that it is a usable deployable proxy.

Falsifiable: the meter tracks true emotion distortion (negative correlation) and separation quality
(alpha). If it does not, there is no reference-free emotion-fidelity signal here and emotion-aware
routing must keep relying on an oracle reference (a real limitation, reported honestly).

Offline; uses resemblyzer (optional frontier dep, dependency-injected so tests need neither it nor
Whisper) + src/prosody.py. Labels: experimental/frontier; references synthetic/silver. No gold tables
touched. Outputs to results/frontier/emotion_fidelity_meter/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .config import PROJECT_ROOT

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "emotion_fidelity_meter"
OVERLAPS = [0.1, 0.3, 0.6, 0.9]
ALPHAS = [0.0, 0.15, 0.3]
EmbedFn = Callable[[np.ndarray], np.ndarray]


# ======================================================================================
# Pure, reference-free signals (no resemblyzer / Whisper) -- unit tested
# ======================================================================================
def embedding_consistency(embeddings: np.ndarray) -> float:
    """Mean cosine similarity of each window embedding to the track centroid, in [0,1]-ish (clamped
    to >=0). 1.0 = all windows agree (one speaker); low = windows split (cross-talk). Reference-free."""
    e = np.asarray(embeddings, dtype=np.float64)
    if e.ndim != 2 or e.shape[0] == 0:
        return 0.0
    if e.shape[0] == 1:
        return 1.0
    centroid = e.mean(axis=0)
    cn = np.linalg.norm(centroid)
    if cn < 1e-12:
        return 0.0
    en = np.linalg.norm(e, axis=1)
    sims = (e @ centroid) / (en * cn + 1e-12)
    return float(max(0.0, np.mean(sims)))


def prosodic_consistency(arousals: list[float]) -> float:
    """Coherence of per-window arousal in [0,1]: 1/(1+std). Constant -> 1.0; high variance -> low."""
    a = np.asarray(list(arousals), dtype=np.float64)
    if a.size == 0:
        return 1.0
    return float(1.0 / (1.0 + np.std(a)))


def fidelity_meter(emb_consistency: float, pros_consistency: float, w_embedding: float = 0.6) -> float:
    """Combined reference-free emotion-fidelity meter in [0,1] (higher = better-preserved emotion).
    Weighted toward the speaker-embedding term (the stronger cross-talk signal, cf. #12)."""
    w = max(0.0, min(1.0, w_embedding))
    return float(max(0.0, min(1.0, w * emb_consistency + (1.0 - w) * pros_consistency)))


def _pearson(x: list[float], y: list[float]) -> float:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.size < 2 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def summarize_meter(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Validation (analysis-only): does the reference-free meter track the true emotion distortion and
    the leakage alpha? Negative correlations mean the meter is a usable deployable proxy."""
    meter = [float(r["meter"]) for r in rows]
    dist = [float(r["emo_distortion"]) for r in rows]
    alpha = [float(r["alpha"]) for r in rows]
    by = []
    for a in sorted(set(alpha)):
        at = [r for r in rows if float(r["alpha"]) == a]
        by.append({"alpha": a, "n": len(at),
                   "mean_meter": round(float(np.mean([float(r["meter"]) for r in at])), 6),
                   "mean_distortion": round(float(np.mean([float(r["emo_distortion"]) for r in at])), 6)})
    return {
        "n": len(rows),
        "pearson_meter_distortion": round(_pearson(meter, dist), 6),
        "pearson_meter_alpha": round(_pearson(meter, alpha), 6),
        "by_alpha": by,
    }


# ======================================================================================
# resemblyzer embedder (lazy; offline) + Whisper-free driver
# ======================================================================================
def track_signals(wav: np.ndarray, embed: EmbedFn) -> dict[str, float]:
    """Reference-free per-track signals over the active region's windows."""
    from .emotion_separation_tax import active_region
    from .prosody import arousal_index, prosodic_features
    from .speaker_conditioned_gate import HOP, WIN, frame_windows

    x = np.asarray(wav, dtype=np.float32)
    s, e = active_region(x)
    seg = x[s:e] if e > s else x
    windows = frame_windows(seg.size, WIN, HOP)
    if len(windows) < 2:
        return {"emb_consistency": 1.0, "pros_consistency": 1.0,
                "meter": fidelity_meter(1.0, 1.0)}
    embs = np.array([np.asarray(embed(seg[a:b]), dtype=np.float64) for a, b in windows])
    arousals = [arousal_index(prosodic_features(seg[a:b])) for a, b in windows]
    ec = embedding_consistency(embs)
    pc = prosodic_consistency(arousals)
    return {"emb_consistency": round(ec, 6), "pros_consistency": round(pc, 6),
            "meter": round(fidelity_meter(ec, pc), 6)}


def run_meter(out_dir: Path, num_pairs: int, overlaps: list[float], alphas: list[float]) -> dict[str, Any]:
    from .emotion_separation_tax import active_region, leak
    from .generate_synthetic_overlap import build_mixture, read_mono_audio
    from .prosody import prosodic_features, prosody_distance
    from .separation_tax_phase import select_pairs
    from .speaker_conditioned_gate import resemblyzer_embedder

    out_dir.mkdir(parents=True, exist_ok=True)
    plans = select_pairs(num_pairs)
    embed = resemblyzer_embedder()
    print(f"[fidelity] pairs={len(plans)} overlaps={overlaps} alphas={alphas}", flush=True)

    rows: list[dict[str, Any]] = []
    for pi, plan in enumerate(plans):
        s1, s2 = read_mono_audio(plan.con_path), read_mono_audio(plan.pro_path)
        for overlap in overlaps:
            _, t1, t2, _ = build_mixture(s1, s2, overlap)
            r1, r2 = active_region(t1), active_region(t2)
            ref1 = prosodic_features(t1[r1[0]:r1[1]])
            ref2 = prosodic_features(t2[r2[0]:r2[1]])
            for alpha in alphas:
                for (tk, to, region, ref) in ((t1, t2, r1, ref1), (t2, t1, r2, ref2)):
                    sep = leak(tk, to, alpha)
                    sig = track_signals(sep, embed)
                    # oracle validation target (NOT used by the meter): true emotion distortion
                    s, e = region
                    seg = sep[s:e] if e > s else sep
                    dist = prosody_distance(ref, prosodic_features(seg))["emotional_distortion"]
                    rows.append({
                        "pair_id": pi, "overlap_ratio": overlap, "alpha": alpha,
                        "emb_consistency": sig["emb_consistency"], "pros_consistency": sig["pros_consistency"],
                        "meter": sig["meter"], "emo_distortion": round(float(dist), 6),
                    })
        print(f"[fidelity] pair {pi + 1}/{len(plans)} done", flush=True)

    curve = out_dir / "fidelity_curve.csv"
    with curve.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    summary = summarize_meter(rows)
    (out_dir / "fidelity_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[fidelity] pearson(meter, true_distortion)={summary['pearson_meter_distortion']}  "
          f"pearson(meter, alpha)={summary['pearson_meter_alpha']}  n={summary['n']}", flush=True)
    try:
        render_figure(out_dir, rows, summary)
    except Exception as exc:
        print(f"[fidelity] figure skipped: {exc}", flush=True)
    print(f"[fidelity] wrote {curve} + fidelity_summary.json (rows={len(rows)})", flush=True)
    return {"summary": summary, "n_rows": len(rows)}


def render_figure(out_dir: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> Path | None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))
    colors = {0.0: "#4c78a8", 0.15: "#54a24b", 0.3: "#e45756"}
    for a in sorted({float(r["alpha"]) for r in rows}):
        at = [r for r in rows if float(r["alpha"]) == a]
        ax1.scatter([r["meter"] for r in at], [r["emo_distortion"] for r in at],
                    s=22, color=colors.get(a, "#888"), label=f"α={a:g}", alpha=0.8)
    ax1.set_xlabel("reference-free fidelity meter (higher = cleaner)")
    ax1.set_ylabel("true emotion distortion (oracle)")
    ax1.set_title(f"Meter vs truth (r={summary['pearson_meter_distortion']})")
    ax1.legend(fontsize=8); ax1.grid(alpha=0.3)
    by = summary["by_alpha"]
    ax2.plot([b["alpha"] for b in by], [b["mean_meter"] for b in by], "-o", color="#4c78a8", label="mean meter")
    ax2.plot([b["alpha"] for b in by], [b["mean_distortion"] for b in by], "-s", color="#e45756", label="mean true distortion")
    ax2.set_xlabel("cross-talk leakage α (separation quality)")
    ax2.set_title(f"Meter falls as leakage rises (r={summary['pearson_meter_alpha']})")
    ax2.legend(fontsize=8); ax2.grid(alpha=0.3)
    fig.suptitle("Reference-free emotion-fidelity meter tracks true distortion + separation quality (zh)")
    fig.tight_layout()
    fig_path = out_dir / "emotion_fidelity_meter.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    print(f"[fidelity] wrote {fig_path}", flush=True)
    return fig_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reference-free emotion-fidelity meter (frontier).")
    p.add_argument("--pairs", type=int, default=8)
    p.add_argument("--overlaps", type=str, default="0.1,0.3,0.6,0.9")
    p.add_argument("--alphas", type=str, default="0.0,0.15,0.3")
    p.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    run_meter(Path(args.out_dir), args.pairs,
              [float(o) for o in args.overlaps.split(",") if o.strip()],
              [float(a) for a in args.alphas.split(",") if a.strip()])


if __name__ == "__main__":
    main()
