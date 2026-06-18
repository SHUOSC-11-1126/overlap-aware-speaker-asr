"""Lexical Emotion Separation Tax + tri-modal agreement (experimental/frontier).

Extends the emotion frontier to the TEXT/VALENCE side and unifies three emotion-relevant views of the
"when should we separate?" decision on identical conditions, in a single Whisper pass:

  - CER benefit              = CER(mixed) - CER(separated)        (text correctness; >0 => separate)
  - acoustic-arousal benefit = prosody_dist(mixed) - prosody_dist(sep)  (audio arousal; src/prosody.py)
  - lexical-valence benefit  = lex_dist(mixed)   - lex_dist(sep)        (text emotion; src/lexical_emotion.py)

The question: do the three objectives AGREE on whether to separate, and does separation preserve a
speaker's textual (valence) emotion the way #14 showed for acoustic arousal? Lexical emotion is read off
the ASR transcript, so unlike acoustic prosody it is directly exposed to ASR ERRORS (a polarity flip
支持<->反对 is a large lexical-emotion distortion even at small CER) — making this a sharp test of
whether the ASR separation tax also taxes textual emotion.

Reference is label-free: the verified/source transcript's own lexical emotion (mirrors CER's reference).
Separation quality is the cross-talk leakage knob from emotion_separation_tax (alpha; 0=oracle).

Labels: experimental/frontier; ASR Whisper-tiny; references synthetic/silver. No gold tables touched.
Outputs to results/frontier/lexical_emotion_tax/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .arousal_asr_probe import pearson
from .config import PROJECT_ROOT
from .emotion_separation_tax import active_region, leak
from .lexical_emotion import lexical_distance
from .prosody import prosody_distance, prosodic_features

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "lexical_emotion_tax"
OVERLAPS = [0.0, 0.1, 0.3, 0.6, 0.9]
ALPHA = 0.15  # realistic separator leakage for the tri-modal cross-link


# ======================================================================================
# Pure logic (no Whisper/librosa) -- unit tested
# ======================================================================================
def _sign(x: float) -> int:
    return 1 if x > 1e-9 else (-1 if x < -1e-9 else 0)


def agreement_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-overlap means of the three benefits + pairwise Pearson correlations + sign-agreement
    fractions. CER/distances are post-hoc; the separation choice is never made from them here."""
    cer = [float(r["cer_benefit"]) for r in rows]
    aco = [float(r["acoustic_benefit"]) for r in rows]
    lex = [float(r["lexical_benefit"]) for r in rows]

    def agree_frac(a: list[float], b: list[float]) -> float:
        pairs = [(x, y) for x, y in zip(a, b) if _sign(x) != 0 and _sign(y) != 0]
        return round(sum(1 for x, y in pairs if _sign(x) == _sign(y)) / len(pairs), 6) if pairs else float("nan")

    by_overlap = []
    for ov in sorted({float(r["overlap_ratio"]) for r in rows}):
        at = [r for r in rows if float(r["overlap_ratio"]) == ov]
        by_overlap.append({
            "overlap_ratio": ov, "n": len(at),
            "mean_cer_benefit": round(float(np.mean([float(r["cer_benefit"]) for r in at])), 6),
            "mean_acoustic_benefit": round(float(np.mean([float(r["acoustic_benefit"]) for r in at])), 6),
            "mean_lexical_benefit": round(float(np.mean([float(r["lexical_benefit"]) for r in at])), 6),
        })
    return {
        "n": len(rows),
        "pearson_cer_lexical": round(pearson(cer, lex), 6) if len(rows) > 1 else float("nan"),
        "pearson_cer_acoustic": round(pearson(cer, aco), 6) if len(rows) > 1 else float("nan"),
        "pearson_acoustic_lexical": round(pearson(aco, lex), 6) if len(rows) > 1 else float("nan"),
        "sign_agree_cer_lexical": agree_frac(cer, lex),
        "sign_agree_cer_acoustic": agree_frac(cer, aco),
        "sign_agree_acoustic_lexical": agree_frac(aco, lex),
        "by_overlap": by_overlap,
    }


# ======================================================================================
# Whisper driver
# ======================================================================================
def run_lexical_tax(out_dir: Path, num_pairs: int, overlaps: list[float], alpha: float) -> dict[str, Any]:
    import whisper

    from .evaluate_cer import compute_cer
    from .generate_synthetic_overlap import build_mixture, read_mono_audio
    from .separation_tax_phase import select_pairs, transcribe_with_signals

    out_dir.mkdir(parents=True, exist_ok=True)
    plans = select_pairs(num_pairs)
    model = whisper.load_model("tiny")
    print(f"[lex-tax] pairs={len(plans)} overlaps={overlaps} alpha={alpha}", flush=True)

    def tx(a: np.ndarray) -> str:
        return transcribe_with_signals(model, np.asarray(a, dtype=np.float32), "greedy")["text"]

    def acoustic_dist(positioned: np.ndarray, region: tuple[int, int], ref_feat: dict[str, float]) -> float:
        s, e = region
        seg = positioned[s:e] if e > s else positioned
        return prosody_distance(ref_feat, prosodic_features(seg))["emotional_distortion"]

    rows: list[dict[str, Any]] = []
    for pi, plan in enumerate(plans):
        s1, s2 = read_mono_audio(plan.con_path), read_mono_audio(plan.pro_path)
        ref_text = plan.con_text + plan.pro_text
        for overlap in overlaps:
            mixed, t1, t2, _ = build_mixture(s1, s2, overlap)
            r1, r2 = active_region(t1), active_region(t2)
            sep1, sep2 = leak(t1, t2, alpha), leak(t2, t1, alpha)
            # --- text (CER + lexical emotion) ---
            mixed_hyp = tx(mixed)
            sep_hyp = tx(sep1) + tx(sep2)
            cer_benefit = compute_cer(ref_text, mixed_hyp)["cer"] - compute_cer(ref_text, sep_hyp)["cer"]
            lex_benefit = (lexical_distance(ref_text, mixed_hyp)["combined"]
                           - lexical_distance(ref_text, sep_hyp)["combined"])
            # --- audio (acoustic arousal) ---
            ref1, ref2 = prosodic_features(t1[r1[0]:r1[1]]), prosodic_features(t2[r2[0]:r2[1]])
            d_mix = np.mean([acoustic_dist(mixed, r1, ref1), acoustic_dist(mixed, r2, ref2)])
            d_sep = np.mean([acoustic_dist(sep1, r1, ref1), acoustic_dist(sep2, r2, ref2)])
            rows.append({
                "pair_id": pi, "overlap_ratio": overlap, "alpha": alpha,
                "cer_benefit": round(float(cer_benefit), 6),
                "acoustic_benefit": round(float(d_mix - d_sep), 6),
                "lexical_benefit": round(float(lex_benefit), 6),
            })
        print(f"[lex-tax] pair {pi + 1}/{len(plans)} done", flush=True)

    curve = out_dir / "lexical_tax_curve.csv"
    with curve.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    summary = agreement_summary(rows)
    (out_dir / "lexical_tax_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[lex-tax] pearson CER~lexical={summary['pearson_cer_lexical']} "
          f"CER~acoustic={summary['pearson_cer_acoustic']} acoustic~lexical={summary['pearson_acoustic_lexical']}", flush=True)
    print(f"[lex-tax] sign-agree CER~lexical={summary['sign_agree_cer_lexical']} "
          f"CER~acoustic={summary['sign_agree_cer_acoustic']}", flush=True)
    try:
        render_figure(out_dir, summary)
    except Exception as exc:
        print(f"[lex-tax] figure skipped: {exc}", flush=True)
    print(f"[lex-tax] wrote {curve} + lexical_tax_summary.json (rows={len(rows)})", flush=True)
    return {"summary": summary, "n_rows": len(rows)}


def render_figure(out_dir: Path, summary: dict[str, Any]) -> Path | None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by = summary["by_overlap"]
    ov = [b["overlap_ratio"] for b in by]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(ov, [b["mean_cer_benefit"] for b in by], "-o", color="#e45756", label="ASR/CER benefit")
    ax.plot(ov, [b["mean_acoustic_benefit"] for b in by], "-s", color="#4c78a8", label="acoustic-arousal benefit")
    ax.plot(ov, [b["mean_lexical_benefit"] for b in by], "-^", color="#54a24b", label="lexical-valence benefit")
    ax.axhline(0.0, color="black", lw=0.9, ls=":")
    ax.set_xlabel("overlap ratio")
    ax.set_ylabel("benefit of separating (>0 ⇒ separate)")
    ax.set_title(f"Tri-modal separation benefit (Whisper-tiny, zh; α={summary['by_overlap'] and ALPHA})\n"
                 f"CER~lexical r={summary['pearson_cer_lexical']}, CER~acoustic r={summary['pearson_cer_acoustic']}")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig_path = out_dir / "lexical_emotion_tax.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    print(f"[lex-tax] wrote {fig_path}", flush=True)
    return fig_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Lexical Emotion Separation Tax + tri-modal agreement (frontier).")
    p.add_argument("--pairs", type=int, default=8)
    p.add_argument("--overlaps", type=str, default="0.0,0.1,0.3,0.6,0.9")
    p.add_argument("--alpha", type=float, default=ALPHA)
    p.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    run_lexical_tax(Path(args.out_dir), args.pairs,
                    [float(o) for o in args.overlaps.split(",") if o.strip()], args.alpha)


if __name__ == "__main__":
    main()
