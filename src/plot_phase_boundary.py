"""Plotting functions for the separation phase boundary analysis.

Provides enhanced phase diagram plots with boundary markers, LOWESS
smoothed crossover lines, and bootstrap probability curves.

Label: ``experimental/frontier`` — does not replace stable gold benchmark claims.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _rgb(hex_str: str) -> tuple[float, float, float]:
    """Convert hex colour to 0–1 RGB tuple."""
    h = hex_str.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


# ── palette ───────────────────────────────────────────────────────────────────

COLOUR_MAP = {
    "stable/gold": "#d62728",
    "synthetic/silver": "#1f77b4",
    "synthetic/silver_v2": "#2ca02c",
}


# ── common helpers ────────────────────────────────────────────────────────────


def _extract_scatter_data(
    points: list[dict[str, Any]],
) -> dict[str, tuple[list[float], list[float]]]:
    """Group points by source_label, returning {label: (xs, ys)}."""
    grouped: dict[str, tuple[list[float], list[float]]] = {}
    for p in points:
        label = str(p.get("source_label", ""))
        r = p.get("overlap_ratio")
        d = p.get("delta_cer_separated")
        if r is None or d is None:
            continue
        try:
            x, y = float(r), float(d)
        except (TypeError, ValueError):
            continue
        grouped.setdefault(label, ([], []))
        grouped[label][0].append(x)
        grouped[label][1].append(y)
    return grouped


# ── enhanced phase diagram ────────────────────────────────────────────────────


def plot_enhanced_phase_diagram(
    points: list[dict[str, Any]],
    trend_rows: list[dict[str, Any]],
    boundary_metadata: dict[str, Any] | None = None,
    out_path: str | Path = "separation_phase_diagram_enhanced.png",
) -> None:
    """Render an enhanced separation phase diagram.

    Shows gold/silver scatter points, binned mean trend line, zero-reference
    line, and (if boundary metadata is provided) crossover marker + LOWESS
    smoothed curve.

    Parameters
    ----------
    points:
        Phase diagram points with ``overlap_ratio``, ``delta_cer_separated``,
        ``source_label``, and ``separation_helps``.
    trend_rows:
        Binned trend rows with ``overlap_bin``, ``mean_delta_cer_separated``,
        and ``sample_count``.
    boundary_metadata:
        Optional crossover / boundary metadata from
        ``separation_phase_boundary.build_boundary_metadata``.
    out_path:
        Output PNG path.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    # ── scatter ──────────────────────────────────────────────────────────
    grouped = _extract_scatter_data(points)
    for label, (xs, ys) in grouped.items():
        colour = COLOUR_MAP.get(label, "#888888")
        marker = "D" if label == "stable/gold" else "o"
        size = 70 if label == "stable/gold" else 36
        ax.scatter(xs, ys, label=label, color=colour, marker=marker, s=size, alpha=0.85)

    # ── trend line ────────────────────────────────────────────────────────
    if trend_rows:
        trend_x = [float(r["overlap_bin"]) for r in trend_rows]
        trend_y = [float(r["mean_delta_cer_separated"]) for r in trend_rows]
        ax.plot(
            trend_x,
            trend_y,
            color="#444444",
            linestyle="--",
            linewidth=1.5,
            label="binned mean delta",
        )

    # ── zero line ─────────────────────────────────────────────────────────
    ax.axhline(0.0, color="#888888", linewidth=1.0, linestyle="-")

    # ── boundary metadata overlay ─────────────────────────────────────────
    if boundary_metadata:
        cr = boundary_metadata.get("crossover_ratio", "")
        if isinstance(cr, (int, float)) and cr != "":
            ax.axvline(
                float(cr),
                color="#e377c2",
                linestyle="-.",
                linewidth=1.5,
                alpha=0.7,
                label=f"crossover ≈ {float(cr):.3f}",
            )
            ci_l = boundary_metadata.get("crossover_ci_lower", "")
            ci_u = boundary_metadata.get("crossover_ci_upper", "")
            if isinstance(ci_l, (int, float)) and isinstance(ci_u, (int, float)):
                ax.axvspan(
                    float(ci_l),
                    float(ci_u),
                    color="#e377c2",
                    alpha=0.12,
                    label=f"95% CI [{float(ci_l):.3f}, {float(ci_u):.3f}]",
                )

    # ── labels ────────────────────────────────────────────────────────────
    ax.set_xlabel("Overlap ratio")
    ax.set_ylabel("ΔCER (separated − mixed)")
    ax.set_title("Separation Phase Diagram (experimental/frontier)")
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


# ── bootstrap probability curve ───────────────────────────────────────────────


def plot_bootstrap_probability_curve(
    dense_trend: list[dict[str, Any]],
    boundary_metadata: dict[str, Any] | None = None,
    out_path: str | Path = "separation_phase_bootstrap_probability.png",
) -> None:
    """Render a bootstrap P(separation helps) curve by overlap bin.

    Parameters
    ----------
    dense_trend:
        Enhanced trend rows with ``overlap_bin``, ``bootstrap_p_helps``,
        ``bootstrap_mean_delta_cer``, ``trend_ci_lower``, ``trend_ci_upper``.
    boundary_metadata:
        Optional crossover metadata to annotate on the plot.
    out_path:
        Output PNG path.
    """
    fig, ax1 = plt.subplots(figsize=(10, 6))

    bins = [float(r["overlap_bin"]) for r in dense_trend]
    p_helps = [float(r["bootstrap_p_helps"]) for r in dense_trend]
    mean_deltas = [float(r["bootstrap_mean_delta_cer"]) for r in dense_trend]
    ci_lowers = [float(r["trend_ci_lower"]) for r in dense_trend]
    ci_uppers = [float(r["trend_ci_upper"]) for r in dense_trend]

    # ── probability bars ──────────────────────────────────────────────────
    colour_p = "#1f77b4"
    ax1.bar(bins, p_helps, width=0.03, color=colour_p, alpha=0.55, label="P(separation helps)")
    ax1.set_xlabel("Overlap ratio")
    ax1.set_ylabel("P(separation helps)", color=colour_p)
    ax1.tick_params(axis="y", labelcolor=colour_p)
    ax1.set_ylim(-0.05, 1.10)

    # ── 0.5 reference ─────────────────────────────────────────────────────
    ax1.axhline(0.5, color=colour_p, linewidth=0.8, linestyle=":", alpha=0.5)

    # ── mean delta CER on twin axis ───────────────────────────────────────
    ax2 = ax1.twinx()
    colour_d = "#d62728"
    ax2.plot(bins, mean_deltas, color=colour_d, marker="o", linewidth=1.5, label="bootstrap mean ΔCER")
    ax2.fill_between(
        bins,
        ci_lowers,
        ci_uppers,
        color=colour_d,
        alpha=0.15,
        label="95% CI",
    )
    ax2.set_ylabel("ΔCER (separated − mixed)", color=colour_d)
    ax2.tick_params(axis="y", labelcolor=colour_d)
    ax2.axhline(0.0, color=colour_d, linewidth=0.8, linestyle="--", alpha=0.4)

    # ── crossover annotation ──────────────────────────────────────────────
    if boundary_metadata:
        cr = boundary_metadata.get("crossover_ratio", "")
        if isinstance(cr, (int, float)) and cr != "":
            ax1.axvline(float(cr), color="#e377c2", linestyle="-.", linewidth=1.5, alpha=0.7)
            ax1.text(
                float(cr) + 0.01,
                0.95,
                f"crossover ≈ {float(cr):.3f}",
                color="#e377c2",
                fontsize=9,
                va="top",
            )

    # ── combined legend ───────────────────────────────────────────────────
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=9)

    ax1.set_title("Bootstrap P(separation helps) vs overlap ratio\n(experimental/frontier)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
