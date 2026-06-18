"""Frontier capstone hero figure (issue #840): all five ASR×LLM + emotion + speaker results on one canvas.

Reads ONLY the committed result summary.json files — no experiment re-run. Synthesizes:
  #831 Semantic Emotion Tax · #833 Anchored Repair · #835 Tri-modal Fusion ·
  #814 Noise-Robust Router · #838 Speaker Attribution.
Label: qualitative/demo (synthesis of experimental/frontier results). No gold tables touched.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import PROJECT_ROOT

FRONTIER = PROJECT_ROOT / "results" / "frontier"
OUT = FRONTIER / "asr_llm_frontier_capstone.png"

RESULTS = {
    "semantic_emotion_tax": "Semantic Emotion Tax (#831)\nLLM reads implicit emotion 7x lexicon",
    "emotion_anchored_repair": "Anchored Repair (#833)\nanchoring does NOT cure over-correction",
    "emotion_modality_fusion": "Tri-modal Fusion (#835)\nfusion helps semantic, not acoustic",
    "noise_robust_router": "Noise-Robust Router (#814)\nbeats both fixed, ~92% oracle gap",
    "llm_speaker_attribution": "Speaker Attribution (#838)\naffect encodes role, sign isn't free",
}


def extract_headlines(summaries: dict) -> dict:
    """Pull each experiment's headline numbers from its summary dict (pure; robust to missing keys)."""
    out: dict = {}
    s = summaries.get("semantic_emotion_tax")
    if s and "H1_coverage" in s:
        out["semantic_emotion_tax"] = {"LLM": s["H1_coverage"]["llm_coverage_rate"],
                                       "lexicon": s["H1_coverage"]["lexical_firing_rate"]}
    s = summaries.get("emotion_anchored_repair")
    if s and "mean_cer_before" in s:
        out["emotion_anchored_repair"] = {"no-repair": s["mean_cer_before"], "naive": s["mean_cer_naive"],
                                          "anchored": s["mean_cer_anchored"]}
    s = summaries.get("emotion_modality_fusion")
    if s and "by_target" in s:
        ac, se = s["by_target"]["acoustic_emotion_damage"], s["by_target"]["semantic_emotion_damage"]
        out["emotion_modality_fusion"] = {"acou\nfused": ac["fused_r2"], "acou\nbest1": ac["best_single_r2"],
                                          "sem\nfused": se["fused_r2"], "sem\nbest1": se["best_single_r2"]}
    s = summaries.get("noise_robust_router")
    if s and "pooled" in s:
        p = s["pooled"]
        out["noise_robust_router"] = {"mixed": p["mean_cer_mixed"], "gate": p["mean_cer_speaker_gate"],
                                      "router": p["mean_cer_router"], "oracle": p["mean_cer_oracle"]}
    s = summaries.get("llm_speaker_attribution")
    if s and "llm_attribution_accuracy" in s:
        out["llm_speaker_attribution"] = {"naive": s["llm_attribution_accuracy"],
                                          "calibrated": s["calibrated_attribution_accuracy"], "chance": 0.5}
    return out


def load_summaries() -> dict:
    out = {}
    for key in RESULTS:
        p = FRONTIER / key / "summary.json"
        if p.exists():
            try:
                out[key] = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    return out


def render(headlines: dict, path: Path = OUT) -> Path | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    axes = axes.ravel()
    palette = ["#4361ee", "#f72585", "#4cc9f0", "#2a9d8f", "#ff9f1c", "#8338ec"]
    for ax, key in zip(axes, RESULTS):
        h = headlines.get(key, {})
        ax.set_title(RESULTS[key], fontsize=10)
        if not h:
            ax.text(0.5, 0.5, "(no data)", ha="center"); ax.axis("off"); continue
        labels, vals = list(h.keys()), list(h.values())
        ax.bar(range(len(vals)), vals, color=palette[:len(vals)])
        ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, fontsize=8)
        for i, v in enumerate(vals):
            ax.text(i, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
        ax.grid(alpha=0.25, axis="y")
    # 6th panel: the unifying thread as text
    ax = axes[5]
    ax.axis("off")
    ax.text(0.0, 1.0,
            "The reference-free thread\n"
            "─────────────────────────\n"
            "• Local LLM reads implicit emotion the\n  lexicon misses (#831), but emotion→role\n"
            "  & emotion→repair signs aren't free\n  (#833, #838).\n"
            "• The cheap DECODER signal wins where\n  it counts: compression-ratio routes\n"
            "  separate-vs-mixed and recovers ~92%\n  of the oracle gap (#814).\n"
            "• Acoustic arousal > text-emotion for\n  acoustic emotion-damage (#835).\n\n"
            "Deploy: route text by decoder degeneracy;\nread emotion acoustically; use the LLM for\n"
            "coverage, not for free-lunch repair/attribution.",
            fontsize=9, va="top", family="monospace")
    fig.suptitle("Overlap-aware Speaker ASR — ASR×LLM + Emotion + Speaker Frontier (Mode C/D capstone)",
                 fontsize=13, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def main(argv=None) -> None:
    argparse.ArgumentParser(description="Frontier capstone hero figure (#840)").parse_args(argv)
    headlines = extract_headlines(load_summaries())
    out = render(headlines)
    print(f"[capstone] extracted {len(headlines)}/5 results; wrote {out}")


if __name__ == "__main__":
    main()
