"""Objective-aware decoupled routing: recover BOTH text and emotion in overlapping speech (frontier).

The capstone that operationalizes findings #14–#17. They established:
  #14  separation HELPS per-speaker emotion at every overlap but HURTS ASR at low/mid overlap —
       the separate-or-not decision is objective-dependent.
  #15  emotion does not predict ASR difficulty (asymmetric); keep the ASR router on its own signals.
  #16  the three modalities (CER, acoustic, lexical) don't share one optimal separation decision.
  #17  an LLM critic does not beat the cheap reference-free signals.

If a system must output BOTH an accurate transcript AND each speaker's emotion, a SINGLE separate-or-not
switch is wrong: tuned for ASR it keeps low/mid-overlap audio mixed (avoiding hallucination) and thereby
forfeits the emotional prosody that separation would have recovered. The fix is OBJECTIVE-AWARE
DECOUPLING: route the TEXT objective by the ASR-optimal decision, but ALWAYS read EMOTION from the
separated track (emotion has no separation tax, #14).

This module quantifies, per utterance, the cost of NOT decoupling (the "coupling cost") and the joint
(CER, emotion-fidelity) regret of each strategy vs a two-objective oracle. The text route here is the
ASR-optimal (argmin-CER) choice — an oracle TEXT router, used to isolate the decoupling benefit (the
novelty is the decoupling, not the text router; any real reference-free router only loses text quality,
never changes the emotion-side argument). CER/emotion are post-hoc; emotion is gain-invariant prosody
distance to the clean source (src/prosody.py), label-free.

Falsifiable: decoupled Pareto-dominates the coupled single-switch system (same CER, lower emotion
distortion) with a NON-TRIVIAL mean coupling cost concentrated at low/mid overlap. If the coupling cost
is ~0, the #14 divergence is immaterial in practice (also a result).

Labels: experimental/frontier; ASR Whisper-tiny; references synthetic/silver. No gold tables touched.
Outputs to results/frontier/objective_aware_routing/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "objective_aware_routing"
OVERLAPS = [0.0, 0.1, 0.3, 0.6, 0.9]
ALPHA = 0.15


# ======================================================================================
# Pure routing logic (no Whisper/librosa) -- unit tested
# ======================================================================================
def strategy_outcomes(rec: dict[str, Any]) -> dict[str, tuple[float, float]]:
    """(CER, emotion_distortion) for each strategy on one utterance. `text_route` is the ASR-optimal
    route (argmin CER) precomputed by the driver."""
    cm, cs = float(rec["cer_mixed"]), float(rec["cer_sep"])
    em, es = float(rec["emo_mixed"]), float(rec["emo_sep"])
    route = rec["text_route"]
    cer_route = cs if route == "sep" else cm
    emo_route = es if route == "sep" else em
    return {
        "always_mixed": (cm, em),
        "always_sep": (cs, es),
        "coupled": (cer_route, emo_route),     # one switch: text and emotion both from `route`
        "decoupled": (cer_route, es),          # text from `route`, emotion ALWAYS from separated
        "oracle": (min(cm, cs), min(em, es)),  # best achievable per axis
    }


def coupling_cost(rec: dict[str, Any]) -> float:
    """Emotion fidelity forfeited by tying emotion to the text route = emo[text_route] - emo_sep
    (>=0; positive exactly when the text route is `mixed` while separation would lower emotion distortion)."""
    em, es = float(rec["emo_mixed"]), float(rec["emo_sep"])
    emo_route = es if rec["text_route"] == "sep" else em
    return float(emo_route - es)


def _normalize_regret(records: list[dict[str, Any]], strategies: list[str]) -> dict[str, float]:
    """Mean normalized joint regret per strategy: per-axis regret vs the per-utterance oracle, each
    normalized by that axis's spread across the grid, averaged with equal weight (w=0.5)."""
    outs = [strategy_outcomes(r) for r in records]
    cers = {s: [o[s][0] for o in outs] for s in strategies}
    emos = {s: [o[s][1] for o in outs] for s in strategies}
    all_cer = [c for s in strategies for c in cers[s]]
    all_emo = [e for s in strategies for e in emos[s]]
    cer_span = (max(all_cer) - min(all_cer)) or 1.0
    emo_span = (max(all_emo) - min(all_emo)) or 1.0
    best_cer = [min(o["oracle"][0], min(o[s][0] for s in strategies)) for o in outs]
    best_emo = [min(o["oracle"][1], min(o[s][1] for s in strategies)) for o in outs]
    out: dict[str, float] = {}
    for s in strategies:
        regrets = []
        for i, o in enumerate(outs):
            rc = (o[s][0] - best_cer[i]) / cer_span
            re = (o[s][1] - best_emo[i]) / emo_span
            regrets.append(0.5 * rc + 0.5 * re)
        out[s] = round(float(np.mean(regrets)), 6)
    return out


_STRATS = ["always_mixed", "always_sep", "coupled", "decoupled", "oracle"]


def summarize_routing(records: list[dict[str, Any]]) -> dict[str, Any]:
    outs = [strategy_outcomes(r) for r in records]
    regret = _normalize_regret(records, _STRATS)
    summary: dict[str, Any] = {
        "n": len(records),
        "mean_coupling_cost": round(float(np.mean([coupling_cost(r) for r in records])), 6) if records else 0.0,
    }
    for s in _STRATS:
        summary[f"mean_cer_{s}"] = round(float(np.mean([o[s][0] for o in outs])), 6) if outs else 0.0
        summary[f"mean_emo_{s}"] = round(float(np.mean([o[s][1] for o in outs])), 6) if outs else 0.0
        summary[f"joint_regret_{s}"] = regret[s]
    by = []
    for ov in sorted({float(r["overlap_ratio"]) for r in records}):
        at = [r for r in records if float(r["overlap_ratio"]) == ov]
        by.append({"overlap_ratio": ov, "n": len(at),
                   "mean_coupling_cost": round(float(np.mean([coupling_cost(r) for r in at])), 6)})
    summary["by_overlap"] = by
    return summary


# ======================================================================================
# Whisper + librosa driver
# ======================================================================================
def run_routing(out_dir: Path, num_pairs: int, overlaps: list[float], alpha: float) -> dict[str, Any]:
    import whisper

    from .emotion_separation_tax import active_region, leak
    from .evaluate_cer import compute_cer
    from .generate_synthetic_overlap import build_mixture, read_mono_audio
    from .prosody import prosodic_features, prosody_distance
    from .separation_tax_phase import select_pairs, transcribe_with_signals

    out_dir.mkdir(parents=True, exist_ok=True)
    plans = select_pairs(num_pairs)
    model = whisper.load_model("tiny")
    print(f"[obj-route] pairs={len(plans)} overlaps={overlaps} alpha={alpha}", flush=True)

    def tx(a: np.ndarray) -> str:
        return transcribe_with_signals(model, np.asarray(a, dtype=np.float32), "greedy")["text"]

    def emo_dist(positioned: np.ndarray, region: tuple[int, int], ref_feat: dict[str, float]) -> float:
        s, e = region
        seg = positioned[s:e] if e > s else positioned
        return prosody_distance(ref_feat, prosodic_features(seg))["emotional_distortion"]

    records: list[dict[str, Any]] = []
    for pi, plan in enumerate(plans):
        s1, s2 = read_mono_audio(plan.con_path), read_mono_audio(plan.pro_path)
        ref_text = plan.con_text + plan.pro_text
        for overlap in overlaps:
            mixed, t1, t2, _ = build_mixture(s1, s2, overlap)
            r1, r2 = active_region(t1), active_region(t2)
            sep1, sep2 = leak(t1, t2, alpha), leak(t2, t1, alpha)
            cer_mixed = compute_cer(ref_text, tx(mixed))["cer"]
            cer_sep = compute_cer(ref_text, tx(sep1) + tx(sep2))["cer"]
            ref1, ref2 = prosodic_features(t1[r1[0]:r1[1]]), prosodic_features(t2[r2[0]:r2[1]])
            emo_mixed = float(np.mean([emo_dist(mixed, r1, ref1), emo_dist(mixed, r2, ref2)]))
            emo_sep = float(np.mean([emo_dist(sep1, r1, ref1), emo_dist(sep2, r2, ref2)]))
            records.append({
                "pair_id": pi, "overlap_ratio": overlap,
                "cer_mixed": round(cer_mixed, 6), "cer_sep": round(cer_sep, 6),
                "emo_mixed": round(emo_mixed, 6), "emo_sep": round(emo_sep, 6),
                "text_route": "sep" if cer_sep < cer_mixed else "mixed",
            })
        print(f"[obj-route] pair {pi + 1}/{len(plans)} done", flush=True)

    curve = out_dir / "routing_curve.csv"
    with curve.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(records[0].keys()))
        w.writeheader()
        w.writerows(records)
    summary = summarize_routing(records)
    (out_dir / "routing_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[obj-route] coupled (CER {summary['mean_cer_coupled']}, emo {summary['mean_emo_coupled']}) vs "
          f"decoupled (CER {summary['mean_cer_decoupled']}, emo {summary['mean_emo_decoupled']})", flush=True)
    print(f"[obj-route] mean coupling cost={summary['mean_coupling_cost']}  "
          f"joint regret coupled={summary['joint_regret_coupled']} decoupled={summary['joint_regret_decoupled']}", flush=True)
    try:
        render_figure(out_dir, summary)
    except Exception as exc:
        print(f"[obj-route] figure skipped: {exc}", flush=True)
    print(f"[obj-route] wrote {curve} + routing_summary.json (records={len(records)})", flush=True)
    return {"summary": summary, "n_records": len(records)}


def render_figure(out_dir: Path, summary: dict[str, Any]) -> Path | None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    str3 = ["always_mixed", "always_sep", "coupled", "decoupled", "oracle"]
    labels = ["always\nmixed", "always\nsep", "coupled\n(1 switch)", "decoupled\n(ours)", "oracle"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.8))
    cers = [summary[f"mean_cer_{s}"] for s in str3]
    emos = [summary[f"mean_emo_{s}"] for s in str3]
    colors = ["#999999", "#bbbbbb", "#e45756", "#54a24b", "#000000"]
    for i, (s, lab) in enumerate(zip(str3, labels)):
        ax1.scatter(cers[i], emos[i], s=90, color=colors[i], label=lab.replace("\n", " "), zorder=3)
        ax1.annotate(lab, (cers[i], emos[i]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    ax1.set_xlabel("mean CER (text quality →)")
    ax1.set_ylabel("mean emotion distortion (→ worse)")
    ax1.set_title("Joint objective: decoupled sits closest to oracle")
    ax1.grid(alpha=0.3)
    by = summary["by_overlap"]
    ax2.bar([f"{b['overlap_ratio']:g}" for b in by], [b["mean_coupling_cost"] for b in by], color="#4c78a8")
    ax2.set_xlabel("overlap ratio")
    ax2.set_ylabel("coupling cost\n(emotion fidelity forfeited)")
    ax2.set_title(f"Coupling cost by overlap (mean={summary['mean_coupling_cost']})")
    ax2.grid(alpha=0.3, axis="y")
    fig.suptitle("Objective-aware decoupling recovers emotion a single ASR switch forfeits (Whisper-tiny, zh)")
    fig.tight_layout()
    fig_path = out_dir / "objective_aware_routing.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    print(f"[obj-route] wrote {fig_path}", flush=True)
    return fig_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Objective-aware decoupled routing capstone (frontier).")
    p.add_argument("--pairs", type=int, default=8)
    p.add_argument("--overlaps", type=str, default="0.0,0.1,0.3,0.6,0.9")
    p.add_argument("--alpha", type=float, default=ALPHA)
    p.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    run_routing(Path(args.out_dir), args.pairs, [float(o) for o in args.overlaps.split(",") if o.strip()], args.alpha)


if __name__ == "__main__":
    main()
