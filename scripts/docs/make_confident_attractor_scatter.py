"""Generate a scatter plot visualizing the "confident attractor" hallucination mechanism.

The causal hallucination probe found that catastrophic hallucination cases are
decoded with HIGHER confidence (avg_logprob closer to 0) and LOWER token
entropy than clean cases — the opposite of what you'd expect. This figure
visualizes that counterintuitive finding, which is the project's key
mechanistic contribution to the Whisper hallucination literature.

Usage:
    .venv/bin/python scripts/docs/make_confident_attractor_scatter.py
"""
from __future__ import annotations

import os
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_PATH = os.path.join(REPO, "results", "frontier", "causal_hallucination_probe", "probe_rows.csv")
OUT_PATH = os.path.join(REPO, "results", "figures", "report", "fig7_confident_attractor_scatter.png")


def load_probe_data():
    """Load probe rows and split into catastrophic vs clean."""
    rows = []
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # Only keep rows with valid avg_logprob and token_entropy
            try:
                logprob = float(r["avg_logprob"])
                entropy = float(r["token_entropy"])
                dom_frac = float(r["dominant_token_fraction"])
            except (ValueError, TypeError):
                continue
            catastrophic = r["catastrophic"].strip().lower() == "true"
            rows.append({
                "avg_logprob": logprob,
                "token_entropy": entropy,
                "dominant_token_fraction": dom_frac,
                "catastrophic": catastrophic,
                "con": r["con"],
                "pro": r["pro"],
                "overlap": float(r["overlap_ratio"]),
                "cer_sep": float(r["cer_sep"]) if r["cer_sep"] else None,
            })
    cat = [r for r in rows if r["catastrophic"]]
    clean = [r for r in rows if not r["catastrophic"]]
    return cat, clean


def main() -> None:
    cat, clean = load_probe_data()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # --- Panel A: avg_logprob vs token_entropy ---
    ax = axes[0]
    if clean:
        ax.scatter(
            [r["token_entropy"] for r in clean],
            [r["avg_logprob"] for r in clean],
            c="#2196F3", alpha=0.5, s=40, label=f"Clean (n={len(clean)})",
            edgecolors="white", linewidth=0.3
        )
    if cat:
        ax.scatter(
            [r["token_entropy"] for r in cat],
            [r["avg_logprob"] for r in cat],
            c="#D32F2F", alpha=0.7, s=60, label=f"Catastrophic (n={len(cat)})",
            edgecolors="white", linewidth=0.3, marker="^"
        )

    # Annotate the means
    if clean:
        mx = np.mean([r["token_entropy"] for r in clean])
        my = np.mean([r["avg_logprob"] for r in clean])
        ax.scatter([mx], [my], c="#1565C0", s=120, marker="X", zorder=5, edgecolors="white", linewidth=1)
        ax.annotate(f"Clean mean\n({mx:.2f}, {my:.2f})", (mx, my), textcoords="offset points",
                    xytext=(10, -15), fontsize=8, color="#1565C0")
    if cat:
        mx = np.mean([r["token_entropy"] for r in cat])
        my = np.mean([r["avg_logprob"] for r in cat])
        ax.scatter([mx], [my], c="#B71C1C", s=120, marker="X", zorder=5, edgecolors="white", linewidth=1)
        ax.annotate(f"Catastrophic mean\n({mx:.2f}, {my:.2f})", (mx, my), textcoords="offset points",
                    xytext=(10, 10), fontsize=8, color="#B71C1C")

    ax.set_xlabel("Token-id Entropy (lower = more locked)", fontsize=10)
    ax.set_ylabel("avg_logprob (higher = more confident)", fontsize=10)
    ax.set_title("(A) The Confident Attractor: hallucination is HIGH confidence + LOW entropy\n"
                 "Catastrophic routes are MORE confident than clean — the opposite of confusion",
                 fontsize=10, loc="left")
    ax.legend(fontsize=9, loc="lower left")
    ax.axhline(0, color="gray", linewidth=0.5, linestyle="--", alpha=0.3)
    ax.set_xlim(-0.1, 3.5)

    # --- Panel B: dominant_token_fraction vs avg_logprob ---
    ax = axes[1]
    if clean:
        ax.scatter(
            [r["dominant_token_fraction"] for r in clean],
            [r["avg_logprob"] for r in clean],
            c="#2196F3", alpha=0.5, s=40, label=f"Clean (n={len(clean)})",
            edgecolors="white", linewidth=0.3
        )
    if cat:
        ax.scatter(
            [r["dominant_token_fraction"] for r in cat],
            [r["avg_logprob"] for r in cat],
            c="#D32F2F", alpha=0.7, s=60, label=f"Catastrophic (n={len(cat)})",
            edgecolors="white", linewidth=0.3, marker="^"
        )

    # Annotate the lock-in zone
    ax.axvspan(0.8, 1.05, alpha=0.1, color="red", label="lock-in zone\n(dom > 0.8)")

    ax.set_xlabel("Dominant Token Fraction (higher = more repetitive)", fontsize=10)
    ax.set_ylabel("avg_logprob (higher = more confident)", fontsize=10)
    ax.set_title("(B) Lock-in signature: catastrophic routes cluster at dom ≈ 0.99\n"
                 "Single-token loops (dom ≈ 0.99) are the Mode-R repetition attractor",
                 fontsize=10, loc="left")
    ax.legend(fontsize=9, loc="lower left")
    ax.axhline(0, color="gray", linewidth=0.5, linestyle="--", alpha=0.3)
    ax.set_xlim(-0.05, 1.1)

    plt.tight_layout()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_PATH.replace(".png", ".pdf"), bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote: {OUT_PATH}")
    print(f"Wrote: {OUT_PATH.replace('.png', '.pdf')}")

    # Print summary stats for verification
    print(f"\nVisualization summary:")
    print(f"  Catastrophic cases: {len(cat)}")
    print(f"  Clean cases: {len(clean)}")
    if cat:
        print(f"  Catastrophic mean avg_logprob: {np.mean([r['avg_logprob'] for r in cat]):.3f}")
        print(f"  Clean mean avg_logprob: {np.mean([r['avg_logprob'] for r in clean]):.3f}")
        print(f"  Catastrophic mean entropy: {np.mean([r['token_entropy'] for r in cat]):.3f}")
        print(f"  Clean mean entropy: {np.mean([r['token_entropy'] for r in clean]):.3f}")


if __name__ == "__main__":
    main()
