"""Generate publication-style figures for REPORT.md.

The figures are intentionally reviewer-facing: they summarize the project
story without creating new benchmark claims. Numerical charts read from the
curated result tables; conceptual phase/surface plots are labeled as decision
views rather than measured metrics.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from matplotlib.colors import Normalize
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


ROOT = Path(__file__).resolve().parents[2]
TABLES = ROOT / "results" / "tables"
OUT = ROOT / "results" / "figures" / "report"

COLORS = {
    "ink": "#1f2937",
    "muted": "#667085",
    "grid": "#d0d5dd",
    "blue": "#1f77b4",
    "blue_light": "#d8ebfb",
    "green": "#2ca02c",
    "green_light": "#dff3df",
    "red": "#d62728",
    "red_light": "#f8d9d9",
    "orange": "#f59e0b",
    "orange_light": "#fff1d6",
    "purple": "#7c3aed",
    "purple_light": "#ede9fe",
    "cyan": "#14b8a6",
    "cyan_light": "#ccfbf1",
    "gray_light": "#f2f4f7",
}


def setup() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 320,
            "font.family": "DejaVu Serif",
            "axes.titlesize": 14,
            "axes.labelsize": 11,
            "axes.edgecolor": "#98a2b3",
            "axes.linewidth": 0.9,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.unicode_minus": False,
        }
    )


def read_csv(name: str) -> list[dict[str, str]]:
    path = TABLES / name
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def rounded_box(
    ax: plt.Axes,
    xy: tuple[float, float],
    width: float,
    height: float,
    text: str,
    face: str,
    edge: str,
    fontsize: int = 9,
    weight: str = "normal",
) -> None:
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.025,rounding_size=0.03",
        linewidth=1.3,
        edgecolor=edge,
        facecolor=face,
        zorder=2,
    )
    ax.add_patch(box)
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight=weight,
        color=COLORS["ink"],
        linespacing=1.15,
        zorder=3,
    )


def arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str = "#475467",
    rad: float = 0.0,
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=14,
            linewidth=1.5,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
            zorder=1,
        )
    )


def figure_system_route_map() -> None:
    fig, ax = plt.subplots(figsize=(13.8, 7.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5,
        0.985,
        "Overlap-Aware ASR Route Map",
        ha="center",
        va="top",
        fontsize=16,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax.text(
        0.5,
        0.905,
        "Reference-free route selection first; CER, cpCER-lite, and speaker-aware CER evaluate only after decisions are fixed.",
        ha="center",
        va="top",
        fontsize=10,
        color=COLORS["muted"],
    )

    rounded_box(ax, (0.05, 0.63), 0.16, 0.12, "mixed audio\nfive gold cases", COLORS["gray_light"], "#98a2b3", 10, "bold")
    rounded_box(ax, (0.30, 0.74), 0.17, 0.105, "mixed\nWhisper", COLORS["blue_light"], COLORS["blue"], 10, "bold")
    rounded_box(ax, (0.30, 0.51), 0.17, 0.105, "separation +\nspeaker-track Whisper", COLORS["green_light"], COLORS["green"], 9, "bold")
    rounded_box(ax, (0.52, 0.51), 0.16, 0.105, "duplicate\nsuppression", COLORS["cyan_light"], COLORS["cyan"], 9, "bold")
    rounded_box(ax, (0.52, 0.74), 0.16, 0.105, "reference-free\nfeatures", COLORS["orange_light"], COLORS["orange"], 9, "bold")
    rounded_box(ax, (0.73, 0.68), 0.19, 0.12, "router v2 /\nrisk-aware selector", COLORS["purple_light"], COLORS["purple"], 10, "bold")
    rounded_box(ax, (0.73, 0.48), 0.19, 0.12, "Mode B\ncompute cascade", COLORS["red_light"], COLORS["red"], 10, "bold")
    rounded_box(ax, (0.35, 0.23), 0.20, 0.11, "evaluation only\nCER / speaker CER / cpCER-lite", COLORS["gray_light"], "#98a2b3", 9, "bold")
    rounded_box(ax, (0.66, 0.23), 0.25, 0.11, "frontier extensions\nMeetEval, profiles, AudioDepth, LLM critic", "#f8fafc", "#64748b", 9)

    arrow(ax, (0.21, 0.69), (0.30, 0.79), COLORS["blue"], 0.08)
    arrow(ax, (0.21, 0.68), (0.30, 0.56), COLORS["green"], -0.08)
    arrow(ax, (0.47, 0.79), (0.52, 0.79), COLORS["orange"], 0.0)
    arrow(ax, (0.47, 0.56), (0.52, 0.56), COLORS["cyan"], 0.0)
    arrow(ax, (0.68, 0.79), (0.73, 0.74), COLORS["purple"], -0.05)
    arrow(ax, (0.68, 0.56), (0.73, 0.55), COLORS["red"], 0.05)
    arrow(ax, (0.82, 0.68), (0.52, 0.34), "#64748b", -0.25)
    arrow(ax, (0.82, 0.48), (0.52, 0.30), "#64748b", 0.15)
    arrow(ax, (0.55, 0.28), (0.66, 0.28), "#64748b", 0.0)

    ax.text(0.30, 0.43, "separated route is useful under heavy/opposite overlap,\nbut can amplify insertion and repetition under light/mid overlap", fontsize=9, color=COLORS["muted"])
    save(fig, "fig1_system_route_map")


def figure_cer_strategy_comparison() -> None:
    rows = read_csv("risk_aware_performance.csv")
    order = [
        ("fixed_mixed_whisper", "Fixed\nmixed"),
        ("fixed_separated_whisper", "Fixed\nseparated"),
        ("fixed_separated_whisper_cleaned", "Cleaned\nseparated"),
        ("risk_aware_selector", "Risk-aware\nselector"),
        ("router_v2", "Router\nv2"),
        ("oracle_best", "Oracle\npost-hoc"),
    ]
    values = {row["strategy"]: float(row["average_cer"]) for row in rows}
    y = np.array([values[key] for key, _ in order])
    labels = [label for _, label in order]
    colors = [COLORS["blue"], COLORS["green"], COLORS["cyan"], COLORS["orange"], COLORS["purple"], "#111827"]

    fig, ax = plt.subplots(figsize=(10.8, 6.2))
    x = np.arange(len(labels))
    bars = ax.bar(x, y, color=colors, edgecolor="#1f2937", linewidth=0.8, width=0.68)
    ax.set_title("Gold Benchmark CER by Route Strategy", fontweight="bold", pad=14)
    ax.set_ylabel("Average CER (lower is better)", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, max(y) * 1.25)
    ax.grid(True, axis="y", color=COLORS["grid"], linewidth=0.7, alpha=0.55)
    ax.set_axisbelow(True)

    for bar, value in zip(bars, y):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.008,
            f"{value:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
            color=COLORS["ink"],
            fontweight="bold",
        )

    ax.annotate(
        "Router v2 matches the post-hoc oracle on the five gold cases\nwithout using CER as an input feature.",
        xy=(4, values["router_v2"]),
        xytext=(2.1, 0.335),
        arrowprops=dict(arrowstyle="->", color=COLORS["purple"], lw=1.5),
        fontsize=9,
        color=COLORS["ink"],
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=COLORS["purple"], alpha=0.95),
    )
    save(fig, "fig2_gold_cer_strategy_comparison")


def figure_separation_phase_plane() -> None:
    case_rows = read_csv("current_results_summary.csv")

    x_grid = np.linspace(0, 1, 48)
    y_grid = np.linspace(0, 1, 48)
    X, Y = np.meshgrid(x_grid, y_grid)

    mixed_safe = np.array([0.35, 0.72])
    separate_helpful = np.array([0.82, 0.30])
    review_risk = np.array([0.66, 0.90])

    separator = 0.82 - 0.66 * X
    risk_gate = 0.72 + 0.10 * np.sin(2 * np.pi * X)
    w_mixed = 1 / (1 + np.exp(-18 * (Y - separator)))
    w_review = 1 / (1 + np.exp(-20 * (Y - risk_gate))) * (0.35 + 0.65 * X)
    w_sep = (1 - w_mixed) * (1 - 0.55 * w_review)

    total = w_mixed + w_sep + w_review + 1e-9
    w_mixed, w_sep, w_review = w_mixed / total, w_sep / total, w_review / total

    dX = (
        w_mixed * (mixed_safe[0] - X)
        + w_sep * (separate_helpful[0] - X)
        + w_review * (review_risk[0] - X)
    )
    dY = (
        w_mixed * (mixed_safe[1] - Y)
        + w_sep * (separate_helpful[1] - Y)
        + w_review * (review_risk[1] - Y)
    )
    dX += 0.12 * (Y - 0.50) * (X - 0.45)
    dY -= 0.10 * (X - 0.55) * (Y - 0.55)
    speed = np.sqrt(dX**2 + dY**2)

    fig, ax = plt.subplots(figsize=(10.7, 7.2))
    norm = Normalize(vmin=0, vmax=1.15)
    stream = ax.streamplot(
        X,
        Y,
        dX,
        dY,
        color=speed,
        cmap="coolwarm",
        norm=norm,
        density=1.35,
        linewidth=1.0,
        arrowsize=1.0,
        integration_direction="both",
    )
    cbar = fig.colorbar(stream.lines, ax=ax, pad=0.025)
    cbar.set_label("Route Change Pressure", fontweight="bold")

    x_sep = np.linspace(0.05, 1.0, 300)
    ax.plot(x_sep, 0.82 - 0.66 * x_sep, "--", color="dimgray", linewidth=1.8, alpha=0.85)
    ax.plot(x_sep, 0.72 + 0.10 * np.sin(2 * np.pi * x_sep), ":", color=COLORS["red"], linewidth=1.5, alpha=0.75)

    ax.scatter(*mixed_safe, s=210, c=COLORS["blue"], edgecolors="black", linewidths=1.0, zorder=10)
    ax.scatter(*separate_helpful, s=210, c=COLORS["green"], edgecolors="black", linewidths=1.0, zorder=10)
    ax.scatter(*review_risk, s=210, c=COLORS["red"], edgecolors="black", linewidths=1.0, zorder=10)
    ax.text(0.39, 0.73, "Mixed-safe\nbasin", color=COLORS["blue"], fontweight="bold", fontsize=10)
    ax.text(0.84, 0.31, "Separate-helpful\nbasin", color=COLORS["green"], fontweight="bold", fontsize=10)
    ax.text(0.69, 0.91, "Review-risk\nbasin", color=COLORS["red"], fontweight="bold", fontsize=10)

    for row in case_rows:
        overlap = float(row["overlap_level"]) / 4.0
        harm = max(0.0, float(row["separated_cer"]) - float(row["mixed_cer"]))
        instability = min(0.95, 0.22 + 1.25 * harm)
        best = row["best_method"]
        color = COLORS["blue"] if best == "mixed_whisper" else COLORS["green"]
        ax.scatter(overlap, instability, s=70, c=color, edgecolors="white", linewidths=1.2, zorder=12)
        dx = -0.115 if overlap > 0.88 else 0.018
        ax.text(overlap + dx, instability + 0.015, row["case_id"].replace("Overlap", ""), fontsize=8, color=COLORS["ink"])

    ax.set_title("Separation Boundary Phase Plane", fontweight="bold", pad=14)
    ax.set_xlabel("Overlap Intensity", fontweight="bold")
    ax.set_ylabel("Transcript Instability / Separation Harm", fontweight="bold")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.set_yticks(np.linspace(0, 1, 6))
    ax.grid(True, color=COLORS["grid"], linewidth=0.7, alpha=0.45)
    ax.set_axisbelow(True)
    ax.text(0.08, 0.08, "Conceptual decision surface using gold-case anchors;\nCER remains evaluation-only.", fontsize=9, color=COLORS["muted"], style="italic")
    save(fig, "fig3_separation_boundary_phase_plane")


def figure_compute_cascade_3d() -> None:
    rows = read_csv("cascade_tiers_comparison.csv")
    strategies = [
        "fixed_mixed_whisper",
        "fixed_separated_whisper",
        "fixed_separated_whisper_cleaned",
        "router_v2_baseline",
        "tiered_cascade_v1",
    ]
    data = {row["strategy"]: row for row in rows}
    costs = np.array([float(data[s]["average_compute_cost"]) for s in strategies])
    cers = np.array([float(data[s]["average_cer"]) for s in strategies])
    risk = np.array([0.18, 0.32, 0.28, 0.20, 0.38])

    x = np.linspace(0.9, 2.25, 44)
    y = np.linspace(0.12, 0.44, 44)
    X, Y = np.meshgrid(x, y)
    Z = (
        0.33
        - 0.13 * np.exp(-((X - 1.62) ** 2 / 0.08 + (Y - 0.20) ** 2 / 0.018))
        - 0.08 * np.exp(-((X - 2.05) ** 2 / 0.09 + (Y - 0.30) ** 2 / 0.024))
        + 0.12 * (Y - 0.24) ** 2
        + 0.025 * (X - 1.75) ** 2
    )
    Z = np.clip(Z, 0.10, 0.34)

    fig = plt.figure(figsize=(11.2, 7.8))
    ax = fig.add_subplot(111, projection="3d")
    surface = ax.plot_surface(
        X,
        Y,
        Z,
        cmap=cm.viridis_r,
        alpha=0.62,
        linewidth=0,
        antialiased=True,
        zorder=1,
    )
    ax.contour(X, Y, Z, zdir="z", offset=0.09, cmap=cm.viridis_r, alpha=0.55)

    colors = [COLORS["blue"], COLORS["green"], COLORS["cyan"], COLORS["purple"], COLORS["red"]]
    labels = ["fixed mixed", "fixed separated", "cleaned", "router v2", "Mode B cascade"]
    ax.scatter(costs, risk, cers, s=95, c=colors, edgecolors="black", linewidths=0.9, depthshade=False, zorder=5)
    for x0, y0, z0, label in zip(costs, risk, cers, labels):
        ax.text(x0 + 0.025, y0 + 0.006, z0 + 0.008, label, fontsize=8, color=COLORS["ink"])

    verts = [
        [(1.0, 0.12, 0.09), (2.2, 0.12, 0.09), (2.2, 0.44, 0.09), (1.0, 0.44, 0.09)]
    ]
    ax.add_collection3d(Poly3DCollection(verts, facecolors="#f8fafc", alpha=0.30, edgecolors="#cbd5e1"))
    ax.set_title("Compute-Aware Cascade Trade-off Surface", fontweight="bold", pad=16)
    ax.set_xlabel("Relative Compute Cost", fontweight="bold", labelpad=10)
    ax.set_ylabel("Instability / Escalation Pressure", fontweight="bold", labelpad=10)
    ax.set_zlabel("Average CER", fontweight="bold", labelpad=10)
    ax.set_xlim(0.9, 2.25)
    ax.set_ylim(0.12, 0.44)
    ax.set_zlim(0.09, 0.34)
    ax.view_init(elev=25, azim=-55)
    ax.xaxis.pane.set_facecolor((1, 1, 1, 1))
    ax.yaxis.pane.set_facecolor((1, 1, 1, 1))
    ax.zaxis.pane.set_facecolor((1, 1, 1, 1))
    cbar = fig.colorbar(surface, ax=ax, shrink=0.68, pad=0.08)
    cbar.set_label("Conceptual CER Surface", fontweight="bold")
    fig.text(0.5, 0.025, "The surface is a visual decision model; labeled points use curated Mode B cascade results.", ha="center", fontsize=9, color=COLORS["muted"])
    save(fig, "fig4_compute_cascade_3d_surface")


def main() -> None:
    setup()
    figure_system_route_map()
    figure_cer_strategy_comparison()
    figure_separation_phase_plane()
    figure_compute_cascade_3d()
    print(f"Wrote report figures to {OUT}")


if __name__ == "__main__":
    main()
