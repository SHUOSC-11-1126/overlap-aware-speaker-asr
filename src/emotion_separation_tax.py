"""The Emotional Separation Tax: when should we separate — for EMOTION? (experimental/frontier)

This is the emotion-dimension analogue of the project's signature result. The ASR thesis is "speech
separation helps Whisper at high overlap but hurts at low overlap." Here we ask the same question for
each speaker's EMOTIONAL PROSODY: in overlapping speech, does separating a speaker's track help or
hurt recovery of their arousal/prosody, relative to reading it off the raw mixture?

Why this is answerable offline with no emotion labels:
  * REFERENCE (truth) = the clean source's own prosody (build_mixture's `track_k` active region is the
    isolated source). No human emotion label is needed — the clean source IS the target, exactly as the
    verified transcript is the target for CER.
  * No real separator ships offline, so separation quality is modelled by a cross-talk LEAKAGE knob:
    `separated_k(alpha) = track_k + alpha * track_other`. alpha=0 is the project's oracle separation;
    alpha=1 equals reading speaker k off the raw mixture. Realistic separators sit around alpha 0.1-0.3.
  * The emotion metric is GAIN-INVARIANT by construction (src/prosody.prosody_distance), so a measured
    "emotional distortion" cannot be just a loudness/SNR change — the loudness change is reported
    separately as gain_component_db. This is the confound control the whole study stands on.

Metric: emotion_recovery_benefit = emotional_distortion(mixed vs source)
                                 - emotional_distortion(separated(alpha) vs source).
  > 0  separation RECOVERS the speaker's emotion (worth separating)
  < 0  separation HURTS it (leave it mixed)

Hypotheses (falsifiable):
  H1  benefit is overlap-dependent with a CROSSOVER: <=0 at low overlap (mixture barely contaminated,
      separation only adds leakage) and >0 at high overlap (mixture dominated by cross-talk) — the
      emotional twin of the ASR separation tax.
  H2  the effect is NOT loudness: gain_component_db stays small relative to emotional_distortion, and
      H1 holds with energy_invariant=True.
  H3  CROSS-LINK: emotion_recovery_benefit correlates with the ASR CER benefit (mixed_cer - sep_cer)
      across the grid — emotion and ASR want the SAME separate-or-not decision. The striking falsifier
      is DIVERGENCE (an overlap band where separation helps one and hurts the other), which would argue
      an emotion-aware system needs its own routing.
  Kill criteria: if at realistic alpha the benefit is flat in overlap AND uncorrelated with CER AND
      dominated by gain_component, emotion is orthogonal to the separation decision here — reported as-is.

Labels: experimental/frontier; ASR Whisper-tiny; references synthetic/silver (clean source prosody +
con/pro snippet text). No gold tables touched. Outputs to results/frontier/emotion_separation_tax/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT
from .prosody import prosodic_features, prosody_distance

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "emotion_separation_tax"
OVERLAPS = [0.0, 0.1, 0.3, 0.6, 0.9]
ALPHAS = [0.0, 0.15, 0.3]   # oracle, good separator, poor separator (cross-talk leakage)
CROSSLINK_ALPHA = 0.15      # realistic separation quality for the ASR cross-link


# ======================================================================================
# Pure logic (no librosa / Whisper) -- unit tested
# ======================================================================================
def leak(track_self: np.ndarray, track_other: np.ndarray, alpha: float) -> np.ndarray:
    """Cross-talk leakage model of an imperfect separator: the target plus a fraction alpha of the
    other speaker. alpha=0 -> oracle separation; alpha=1 -> the raw mixture (in the target's region)."""
    return (np.asarray(track_self, dtype=np.float32) + float(alpha) * np.asarray(track_other, dtype=np.float32)).astype(np.float32)


def active_region(track: np.ndarray) -> tuple[int, int]:
    """(first, last+1) nonzero sample of a positioned single-speaker track. (0,0) if silent."""
    nz = np.nonzero(np.abs(np.asarray(track)) > 0)[0]
    if nz.size == 0:
        return (0, 0)
    return (int(nz[0]), int(nz[-1]) + 1)


def emotion_recovery_benefit(mixed_distortion: float, separated_distortion: float) -> float:
    """benefit > 0 means separation recovers emotion (lower distortion than the raw mixture)."""
    return float(mixed_distortion) - float(separated_distortion)


def aggregate_tax(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-overlap mean emotion benefit + gain component, and whether the benefit sign FLIPS across
    overlap (the H1 crossover that mirrors the ASR separation tax)."""
    by_overlap: list[dict[str, Any]] = []
    for ov in sorted({float(r["overlap_ratio"]) for r in rows}):
        at = [r for r in rows if float(r["overlap_ratio"]) == ov]
        by_overlap.append({
            "overlap_ratio": ov,
            "n": len(at),
            "mean_emotion_benefit": round(float(np.mean([float(r["emotion_benefit"]) for r in at])), 6),
            "mean_gain_component_db": round(float(np.mean([float(r["gain_component_db"]) for r in at])), 6),
        })
    signs = [np.sign(r["mean_emotion_benefit"]) for r in by_overlap if r["mean_emotion_benefit"] != 0.0]
    crossover = len({s for s in signs}) > 1
    return {"by_overlap": by_overlap, "crossover_detected": bool(crossover)}


def correlate_benefits(emotion_benefits: list[float], cer_benefits: list[float]) -> dict[str, float]:
    """Pearson + Spearman between the per-condition emotion benefit and ASR CER benefit (H3). NaN-safe."""
    em = np.asarray(emotion_benefits, dtype=np.float64)
    ce = np.asarray(cer_benefits, dtype=np.float64)
    out = {"pearson": float("nan"), "spearman": float("nan"), "n": int(em.size)}
    if em.size < 2 or np.std(em) == 0 or np.std(ce) == 0:
        return out
    out["pearson"] = round(float(np.corrcoef(em, ce)[0, 1]), 6)
    er, cr = _rankdata(em), _rankdata(ce)
    if np.std(er) > 0 and np.std(cr) > 0:
        out["spearman"] = round(float(np.corrcoef(er, cr)[0, 1]), 6)
    return out


def _rankdata(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, x.size + 1, dtype=np.float64)
    return ranks


# ======================================================================================
# Prosody driver (librosa; no Whisper) -- the cheap, large phase-diagram grid
# ======================================================================================
def _speaker_features(positioned: np.ndarray, region: tuple[int, int]) -> dict[str, float]:
    s, e = region
    seg = positioned[s:e] if e > s else positioned
    return prosodic_features(seg)


def run_prosody_tax(out_dir: Path, num_pairs: int, overlaps: list[float], alphas: list[float]) -> dict[str, Any]:
    from .generate_synthetic_overlap import build_mixture, read_mono_audio
    from .separation_tax_phase import select_pairs

    out_dir.mkdir(parents=True, exist_ok=True)
    plans = select_pairs(num_pairs)
    print(f"[emotion-tax] pairs={len(plans)} overlaps={overlaps} alphas={alphas}", flush=True)
    rows: list[dict[str, Any]] = []
    for pi, plan in enumerate(plans):
        s1, s2 = read_mono_audio(plan.con_path), read_mono_audio(plan.pro_path)
        for overlap in overlaps:
            mixed, t1, t2, _ = build_mixture(s1, s2, overlap)
            r1, r2 = active_region(t1), active_region(t2)
            ref1, ref2 = _speaker_features(t1, r1), _speaker_features(t2, r2)
            mix1, mix2 = _speaker_features(mixed, r1), _speaker_features(mixed, r2)
            d_mix1 = prosody_distance(ref1, mix1)["emotional_distortion"]
            d_mix2 = prosody_distance(ref2, mix2)["emotional_distortion"]
            g_mix1 = prosody_distance(ref1, mix1)["gain_component_db"]
            for alpha in alphas:
                sep1 = _speaker_features(leak(t1, t2, alpha), r1)
                sep2 = _speaker_features(leak(t2, t1, alpha), r2)
                pd1 = prosody_distance(ref1, sep1)
                pd2 = prosody_distance(ref2, sep2)
                b1 = emotion_recovery_benefit(d_mix1, pd1["emotional_distortion"])
                b2 = emotion_recovery_benefit(d_mix2, pd2["emotional_distortion"])
                rows.append({
                    "pair_id": pi, "overlap_ratio": overlap, "alpha": alpha,
                    "emotion_benefit": round(float(np.mean([b1, b2])), 6),
                    "benefit_spk1": round(b1, 6), "benefit_spk2": round(b2, 6),
                    "sep_distortion": round(float(np.mean([pd1["emotional_distortion"], pd2["emotional_distortion"]])), 6),
                    "mixed_distortion": round(float(np.mean([d_mix1, d_mix2])), 6),
                    "arousal_shift": round(float(np.mean([pd1["arousal_distance"], pd2["arousal_distance"]])), 6),
                    "gain_component_db": round(float(np.mean([pd1["gain_component_db"], pd2["gain_component_db"]])), 6),
                })
        print(f"[emotion-tax] pair {pi + 1}/{len(plans)} done", flush=True)

    curve = out_dir / "prosody_tax_curve.csv"
    with curve.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    summary = {str(a): aggregate_tax([r for r in rows if r["alpha"] == a]) for a in alphas}
    (out_dir / "prosody_tax_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[emotion-tax] wrote {curve} + prosody_tax_summary.json (rows={len(rows)})", flush=True)
    for a in alphas:
        by = summary[str(a)]["by_overlap"]
        trace = " ".join(f"{r['overlap_ratio']:g}:{r['mean_emotion_benefit']:+.3f}" for r in by)
        print(f"[emotion-tax] alpha={a} benefit-by-overlap {trace} crossover={summary[str(a)]['crossover_detected']}", flush=True)
    return {"summary": summary, "n_rows": len(rows)}


# ======================================================================================
# ASR x emotion cross-link (Whisper) -- the headline tie-back to the project's CER thesis
# ======================================================================================
def run_crosslink(out_dir: Path, num_pairs: int, overlaps: list[float], alpha: float) -> dict[str, Any]:
    import whisper

    from .evaluate_cer import compute_cer
    from .generate_synthetic_overlap import build_mixture, read_mono_audio
    from .separation_tax_phase import select_pairs, transcribe_with_signals

    out_dir.mkdir(parents=True, exist_ok=True)
    plans = select_pairs(num_pairs)
    model = whisper.load_model("tiny")
    print(f"[crosslink] pairs={len(plans)} overlaps={overlaps} alpha={alpha}", flush=True)

    def tx(a: np.ndarray) -> str:
        return transcribe_with_signals(model, a, "greedy")["text"]

    rows: list[dict[str, Any]] = []
    for pi, plan in enumerate(plans):
        s1, s2 = read_mono_audio(plan.con_path), read_mono_audio(plan.pro_path)
        ref_text = plan.con_text + plan.pro_text
        for overlap in overlaps:
            mixed, t1, t2, _ = build_mixture(s1, s2, overlap)
            r1, r2 = active_region(t1), active_region(t2)
            # ASR benefit: mixed CER vs separated(alpha) CER
            sep1, sep2 = leak(t1, t2, alpha), leak(t2, t1, alpha)
            cer_mixed = compute_cer(ref_text, tx(mixed))["cer"]
            cer_sep = compute_cer(ref_text, tx(sep1) + tx(sep2))["cer"]
            cer_benefit = cer_mixed - cer_sep  # >0: separation helps ASR
            # Emotion benefit at the same alpha (energy-invariant prosody)
            ref1, ref2 = _speaker_features(t1, r1), _speaker_features(t2, r2)
            d_mix = np.mean([prosody_distance(ref1, _speaker_features(mixed, r1))["emotional_distortion"],
                             prosody_distance(ref2, _speaker_features(mixed, r2))["emotional_distortion"]])
            d_sep = np.mean([prosody_distance(ref1, _speaker_features(sep1, r1))["emotional_distortion"],
                             prosody_distance(ref2, _speaker_features(sep2, r2))["emotional_distortion"]])
            rows.append({
                "pair_id": pi, "overlap_ratio": overlap, "alpha": alpha,
                "cer_mixed": round(cer_mixed, 6), "cer_sep": round(cer_sep, 6),
                "cer_benefit": round(float(cer_benefit), 6),
                "emotion_benefit": round(float(d_mix - d_sep), 6),
            })
        print(f"[crosslink] pair {pi + 1}/{len(plans)} done", flush=True)

    tag = f"a{alpha:g}".replace(".", "")
    curve = out_dir / f"crosslink_curve_{tag}.csv"
    with curve.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    corr = correlate_benefits([r["emotion_benefit"] for r in rows], [r["cer_benefit"] for r in rows])
    by_overlap = []
    for ov in sorted({r["overlap_ratio"] for r in rows}):
        at = [r for r in rows if r["overlap_ratio"] == ov]
        by_overlap.append({
            "overlap_ratio": ov,
            "mean_cer_benefit": round(float(np.mean([r["cer_benefit"] for r in at])), 6),
            "mean_emotion_benefit": round(float(np.mean([r["emotion_benefit"] for r in at])), 6),
            "sign_disagreement": bool(np.mean([r["cer_benefit"] for r in at]) < 0 < np.mean([r["emotion_benefit"] for r in at])),
        })
    summary = {"alpha": alpha, "correlation": corr, "by_overlap": by_overlap}
    (out_dir / f"crosslink_summary_{tag}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[crosslink] corr(emotion_benefit, cer_benefit) pearson={corr['pearson']} spearman={corr['spearman']} n={corr['n']}", flush=True)
    return {"summary": summary, "n_rows": len(rows)}


def render_figure(out_dir: Path) -> Path | None:
    summary_path = out_dir / "prosody_tax_summary.json"
    if not summary_path.exists():
        return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    colors = {"0.0": "#4c78a8", "0.15": "#54a24b", "0.3": "#e45756"}
    for a, s in summary.items():
        by = s["by_overlap"]
        ax.plot([r["overlap_ratio"] for r in by], [r["mean_emotion_benefit"] for r in by],
                "-o", color=colors.get(a, "#888"), label=f"separator leakage α={a}")
    ax.axhline(0.0, color="black", lw=0.9, ls=":")
    ax.set_xlabel("overlap ratio")
    ax.set_ylabel("emotion recovery benefit\n(mixed − separated distortion; >0 = separate)")
    ax.set_title("The Emotional Separation Tax (gain-invariant prosody, zh debate)")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig_path = out_dir / "emotion_separation_tax.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    print(f"[emotion-tax] wrote {fig_path}", flush=True)
    return fig_path


def render_crosslink_figure(out_dir: Path) -> Path | None:
    """The money plot: ASR CER benefit vs EMOTION recovery benefit by overlap. Where the two curves
    straddle zero (CER<0, emotion>0) the two objectives DISAGREE on whether to separate."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    summaries = []
    for tag, a in [("a0", "0.0"), ("a015", "0.15")]:
        p = out_dir / f"crosslink_summary_{tag}.json"
        if p.exists():
            summaries.append((a, json.loads(p.read_text(encoding="utf-8"))))
    if not summaries:
        return None
    fig, axes = plt.subplots(1, len(summaries), figsize=(6.2 * len(summaries), 4.6), sharey=True)
    if len(summaries) == 1:
        axes = [axes]
    for ax, (a, s) in zip(axes, summaries):
        by = s["by_overlap"]
        ov = [r["overlap_ratio"] for r in by]
        cer = [r["mean_cer_benefit"] for r in by]
        emo = [r["mean_emotion_benefit"] for r in by]
        ax.plot(ov, cer, "-o", color="#e45756", label="ASR benefit (mixed−sep CER)")
        ax.plot(ov, emo, "-s", color="#4c78a8", label="emotion benefit (mixed−sep prosody)")
        ax.axhline(0.0, color="black", lw=0.9, ls=":")
        for r in by:
            if r.get("sign_disagreement"):
                ax.axvspan(r["overlap_ratio"] - 0.04, r["overlap_ratio"] + 0.04, color="#ffd966", alpha=0.35)
        ax.set_title(f"separator leakage α={a}\n(shaded = objectives disagree)")
        ax.set_xlabel("overlap ratio")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("benefit of separating (>0 ⇒ separate)")
    fig.suptitle("Separation helps emotion but hurts ASR at low/mid overlap — objectives diverge (Whisper-tiny, zh)")
    fig.tight_layout()
    fig_path = out_dir / "emotion_asr_divergence.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    print(f"[crosslink] wrote {fig_path}", flush=True)
    return fig_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Emotional Separation Tax experiment (frontier).")
    p.add_argument("--pairs", type=int, default=8)
    p.add_argument("--overlaps", type=str, default="0.0,0.1,0.3,0.6,0.9")
    p.add_argument("--alphas", type=str, default="0.0,0.15,0.3")
    p.add_argument("--crosslink", action="store_true", help="Run the Whisper ASR x emotion cross-link and exit.")
    p.add_argument("--crosslink-alpha", type=float, default=CROSSLINK_ALPHA, help="Separator leakage alpha for the cross-link.")
    p.add_argument("--figure", action="store_true", help="Render the figure from an existing summary and exit.")
    p.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    overlaps = [float(o) for o in args.overlaps.split(",") if o.strip()]
    if args.figure:
        render_figure(out_dir)
        render_crosslink_figure(out_dir)
        return
    if args.crosslink:
        run_crosslink(out_dir, args.pairs, overlaps, args.crosslink_alpha)
        return
    run_prosody_tax(out_dir, args.pairs, overlaps, [float(a) for a in args.alphas.split(",") if a.strip()])
    render_figure(out_dir)


if __name__ == "__main__":
    main()
