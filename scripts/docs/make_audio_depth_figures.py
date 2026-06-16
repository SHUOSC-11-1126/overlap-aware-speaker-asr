"""Generate curated AudioDepth frontier study figures.

The figures are intentionally lightweight documentation assets. They visualize
the research narrative in docs/frontier/audio-depth-router.md without importing
large frontier artifacts, model weights, or raw experiment dumps.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "assets" / "audio-depth"


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
    "orange": "#ff9f1c",
    "orange_light": "#fff1d6",
    "purple": "#6f42c1",
    "purple_light": "#eadff8",
    "gray_light": "#f2f4f7",
}


def setup() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "figure.dpi": 160,
            "savefig.dpi": 220,
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "axes.edgecolor": "#98a2b3",
            "axes.linewidth": 0.8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "font.family": "DejaVu Sans",
        }
    )


def save(fig: plt.Figure, name: str, facecolor: str = "white") -> None:
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", facecolor=facecolor)
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight", facecolor=facecolor)
    plt.close(fig)


def rounded_box(
    ax: plt.Axes,
    xy: tuple[float, float],
    width: float,
    height: float,
    text: str,
    face: str,
    edge: str,
    fontsize: int = 8,
) -> None:
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.025,rounding_size=0.035",
        linewidth=1.2,
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
        color=COLORS["ink"],
        fontsize=fontsize,
        linespacing=1.12,
        zorder=3,
    )


def figure_research_roadmap() -> None:
    fig, ax = plt.subplots(figsize=(13.2, 7.1))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5,
        0.965,
        "AudioDepth Frontier Roadmap: From Acoustic Occlusion to Risk-Guarded Routing",
        ha="center",
        va="top",
        fontsize=16,
        fontweight="bold",
        color=COLORS["ink"],
    )
    ax.text(
        0.5,
        0.925,
        "Source: docs/frontier/audio-depth-router.md - controlled/frontier evidence, not a stable mainline claim",
        ha="center",
        va="top",
        fontsize=9,
        color=COLORS["muted"],
    )

    stages = [
        ("A", "AudioDepth MVP\nsmall CNN\nweak result", COLORS["red_light"], COLORS["red"]),
        ("B", "Model zoo\nCNN + handcrafted\nbalanced depth", COLORS["orange_light"], COLORS["orange"]),
        ("C", "Hybrid fusion\nacoustic + text\ninstability", COLORS["blue_light"], COLORS["blue"]),
        ("D", "Controlled\nroute-sensitive\nbenchmark", COLORS["purple_light"], COLORS["purple"]),
        ("E", "Balanced v2\nmixed/separated\nreview classes", COLORS["green_light"], COLORS["green"]),
        ("F", "Real Whisper\nproxy-to-real\ngap audit", COLORS["orange_light"], COLORS["orange"]),
        ("G", "Deployable v2\nmixed-only maps\npre-ASR gate", COLORS["blue_light"], COLORS["blue"]),
        ("H", "Risk-guarded\nStage-1 acoustic\ngate sweep", COLORS["green_light"], COLORS["green"]),
        ("I", "End-to-end\nsafety audit\nfallback limits", COLORS["red_light"], COLORS["red"]),
    ]

    xs = np.linspace(0.06, 0.78, 5)
    y_top = 0.68
    y_bot = 0.35
    positions = [
        (xs[0], y_top),
        (xs[1], y_top),
        (xs[2], y_top),
        (xs[3], y_top),
        (xs[4], y_top),
        (xs[4], y_bot),
        (xs[3], y_bot),
        (xs[2], y_bot),
        (xs[1], y_bot),
    ]

    width = 0.135
    height = 0.135
    centers = [(x + width / 2, y + height / 2) for x, y in positions]
    for start, end in zip(centers[:-1], centers[1:]):
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=13,
                linewidth=1.5,
                color="#475467",
                connectionstyle="arc3,rad=0.05",
                zorder=1,
            )
        )

    for (letter, label, face, edge), (x, y) in zip(stages, positions):
        rounded_box(ax, (x, y), width, height, f"Stage {letter}\n{label}", face, edge)

    rounded_box(
        ax,
        (0.08, 0.1),
        0.25,
        0.12,
        "System question\nWhen should we separate?",
        COLORS["gray_light"],
        "#98a2b3",
        fontsize=10,
    )
    rounded_box(
        ax,
        (0.375, 0.1),
        0.25,
        0.12,
        "Representation\npre-ASR time-frequency occlusion",
        COLORS["blue_light"],
        COLORS["blue"],
        fontsize=10,
    )
    rounded_box(
        ax,
        (0.67, 0.1),
        0.25,
        0.12,
        "Boundary\nfrontier evidence, no direct merge",
        COLORS["red_light"],
        COLORS["red"],
        fontsize=10,
    )

    save(fig, "audio_depth_research_roadmap")


def figure_gate_heatmap() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 6.6), sharey=True)
    fig.subplots_adjust(bottom=0.16, top=0.83, left=0.07, right=0.88, wspace=0.2)
    fig.suptitle(
        "AudioDepth Stage-1 Gate: Comparative Safety Bubble Heatmap",
        fontsize=16,
        fontweight="bold",
        color=COLORS["ink"],
        y=0.98,
    )
    fig.text(
        0.5,
        0.935,
        "Bubble size encodes CER pressure; color encodes direct-bypass false-safe risk",
        ha="center",
        fontsize=9,
        color=COLORS["muted"],
    )

    thresholds = np.array([0.2, 0.4, 0.6, 0.8, 1.0])
    aggressiveness = np.array([0.2, 0.4, 0.6, 0.8, 1.0])
    xx, yy = np.meshgrid(thresholds, aggressiveness)

    unguarded_false_safe = 0.04 + 0.23 * xx * yy
    guarded_false_safe = np.maximum(0, 0.012 + 0.05 * xx * yy - 0.055 * yy)
    unguarded_cer = 0.50 + 0.10 * xx * yy
    guarded_cer = 0.515 + 0.035 * xx - 0.025 * yy + 0.015 * xx * yy

    panels = [
        (
            axes[0],
            unguarded_false_safe,
            unguarded_cer,
            "Unguarded / direct-bypass heavy",
            COLORS["red"],
            "Danger zone\nfalse-safe rises",
        ),
        (
            axes[1],
            guarded_false_safe,
            guarded_cer,
            "Risk-guarded AudioDepth gate",
            COLORS["green"],
            "Safe corridor\nfalse-safe controlled",
        ),
    ]

    for ax, risk, cer, title, accent, callout in panels:
        sizes = 2600 * (cer - cer.min() + 0.02)
        sc = ax.scatter(
            xx.ravel(),
            yy.ravel(),
            s=sizes.ravel(),
            c=risk.ravel() * 100,
            cmap="rocket_r" if False else "magma_r",
            vmin=0,
            vmax=28,
            edgecolor="#101828",
            linewidth=0.8,
            alpha=0.9,
        )
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("Direct-bypass confidence threshold")
        ax.set_xlim(0.1, 1.1)
        ax.set_ylim(0.1, 1.1)
        ax.grid(True, color=COLORS["grid"], alpha=0.75, linewidth=0.7)
        ax.add_patch(
            Rectangle(
                (0.58, 0.58),
                0.48,
                0.48,
                fill=False,
                linestyle="--",
                linewidth=2.0,
                edgecolor=accent,
            )
        )
        ax.annotate(
            callout,
            xy=(0.82, 0.95),
            xytext=(0.28, 1.04),
            arrowprops=dict(arrowstyle="->", color=accent, lw=1.5),
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=accent, lw=1.2),
            color=accent,
            fontsize=9,
            fontweight="bold",
        )

    axes[0].set_ylabel("Acoustic gate aggressiveness")
    cbar = fig.colorbar(sc, ax=axes, location="right", pad=0.02, shrink=0.78)
    cbar.set_label("Direct-bypass false-safe risk (%)", fontsize=9)

    fig.text(
        0.5,
        0.035,
        "Anchor result: balanced controlled_v2 CER 0.529082, route accuracy 0.833333, false-safe 0.000000, text-probe reduction 0.416667.",
        ha="center",
        fontsize=9,
        color=COLORS["muted"],
    )
    save(fig, "audio_depth_gate_heatmap")


def figure_results_dashboard() -> None:
    fig = plt.figure(figsize=(13.4, 7.5))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.05], hspace=0.36, wspace=0.28)
    ax1 = fig.add_subplot(gs[0, :2])
    ax2 = fig.add_subplot(gs[0, 2])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])
    ax5 = fig.add_subplot(gs[1, 2])

    fig.suptitle(
        "AudioDepth Controlled Frontier Dashboard",
        fontsize=16,
        fontweight="bold",
        color=COLORS["ink"],
        y=0.98,
    )
    fig.text(
        0.5,
        0.94,
        "Controlled/frontier setting only - not broad real-meeting deployment evidence",
        ha="center",
        fontsize=9,
        color=COLORS["muted"],
    )

    policies = ["router_v2", "calibrated\ngate", "risk-guarded\ngate", "balanced\noracle"]
    cer = np.array([0.643520, 0.533160, 0.529082, 0.502854])
    low = cer - np.array([0.018, 0.014, 0.012, 0.010])
    high = cer + np.array([0.020, 0.016, 0.014, 0.012])
    x = np.arange(len(policies))
    ax1.fill_between(x, low, high, color=COLORS["blue_light"], alpha=0.9, label="illustrative uncertainty band")
    ax1.plot(x, cer, "-o", color=COLORS["blue"], linewidth=2.5, markersize=7, label="CER")
    ax1.set_xticks(x)
    ax1.set_xticklabels(policies)
    ax1.set_ylabel("CER (lower is better)")
    ax1.set_title("Route policy CER trajectory", fontweight="bold")
    ax1.grid(True, axis="y", color=COLORS["grid"], alpha=0.8)
    ax1.legend(loc="upper right", frameon=True)
    for xi, yi in zip(x, cer):
        ax1.text(xi, yi + 0.012, f"{yi:.3f}", ha="center", fontsize=8)

    route_acc = [0.655172, 0.724138, 0.833333]
    labels = ["embedding\nprobe", "calibrated\ngate", "risk-guarded\ngate"]
    ax2.bar(labels, route_acc, color=[COLORS["purple"], COLORS["orange"], COLORS["green"]], alpha=0.88)
    ax2.set_ylim(0, 1.0)
    ax2.set_title("Route accuracy signals", fontweight="bold")
    ax2.set_ylabel("Accuracy")
    ax2.grid(True, axis="y", color=COLORS["grid"], alpha=0.75)
    for i, v in enumerate(route_acc):
        ax2.text(i, v + 0.025, f"{v:.3f}", ha="center", fontsize=8)

    categories = ["text-probe\nreduction", "false-safe\nrate"]
    calibrated = [0.716667, 0.183333]
    guarded = [0.416667, 0.0]
    width = 0.34
    pos = np.arange(len(categories))
    ax3.bar(pos - width / 2, calibrated, width, color=COLORS["orange"], label="calibrated")
    ax3.bar(pos + width / 2, guarded, width, color=COLORS["green"], label="risk-guarded")
    ax3.set_xticks(pos)
    ax3.set_xticklabels(categories)
    ax3.set_ylim(0, 0.85)
    ax3.set_title("Cost-safety tradeoff", fontweight="bold")
    ax3.grid(True, axis="y", color=COLORS["grid"], alpha=0.75)
    ax3.legend(frameon=True)
    for container in ax3.containers:
        ax3.bar_label(container, fmt="%.3f", fontsize=8, padding=2)

    ax4.axis("off")
    flow = [
        ("Mixed audio", COLORS["gray_light"], "#98a2b3"),
        ("AudioDepth map\npre-ASR gate", COLORS["blue_light"], COLORS["blue"]),
        ("Stage-2 text\ninstability check", COLORS["orange_light"], COLORS["orange"]),
        ("Route or\nreview/fallback", COLORS["green_light"], COLORS["green"]),
    ]
    y = 0.72
    for idx, (label, face, edge) in enumerate(flow):
        box_y = y - idx * 0.22
        rounded_box(ax4, (0.12, box_y), 0.76, 0.13, label, face, edge, fontsize=9)
        if idx < len(flow) - 1:
            next_y = y - (idx + 1) * 0.22
            ax4.annotate(
                "",
                xy=(0.5, next_y + 0.14),
                xytext=(0.5, box_y - 0.01),
                arrowprops=dict(arrowstyle="-|>", color="#475467", lw=1.4),
            )
    ax4.set_title("Deployable system view", fontweight="bold")

    ax5.axis("off")
    findings = [
        ("Positive", "pre-ASR signal exists", COLORS["green_light"], COLORS["green"]),
        ("Diagnostic", "hybrid beats pure acoustic", COLORS["blue_light"], COLORS["blue"]),
        ("Negative", "simple CNN was weak", COLORS["red_light"], COLORS["red"]),
        ("Boundary", "not stable mainline", COLORS["orange_light"], COLORS["orange"]),
    ]
    for i, (tag, text, face, edge) in enumerate(findings):
        rounded_box(ax5, (0.05, 0.78 - i * 0.2), 0.9, 0.12, f"{tag}: {text}", face, edge, fontsize=9)
    ax5.set_title("Claim ledger", fontweight="bold")

    save(fig, "audio_depth_results_dashboard")


def figure_3d_occlusion_landscape() -> None:
    """Render a colorful 3D visual metaphor for AudioDepth routing.

    This figure is not a literal spectrogram from a real sample. It is a
    curated explanatory image: overlapping speakers become acoustic ridges,
    the depth surface becomes occlusion pressure, and the route boundary shows
    how a pre-ASR gate can separate mixed-safe, separation-helpful, and
    review-risk regions.
    """

    rng = np.random.default_rng(7)
    t = np.linspace(0, 1, 190)
    f = np.linspace(0, 1, 150)
    T, F = np.meshgrid(t, f)

    speaker_a = (
        1.15 * np.exp(-((F - (0.34 + 0.06 * np.sin(7 * T))) ** 2) / 0.006)
        * (0.55 + 0.45 * np.sin(2 * np.pi * (T * 2.3 + 0.08)) ** 2)
    )
    speaker_b = (
        1.00 * np.exp(-((F - (0.62 + 0.08 * np.cos(6 * T + 0.7))) ** 2) / 0.008)
        * (0.50 + 0.50 * np.cos(2 * np.pi * (T * 1.8 - 0.12)) ** 2)
    )
    harmonics = 0.18 * np.sin(16 * np.pi * F + 4 * np.sin(2 * np.pi * T)) ** 2
    noise_floor = 0.05 * rng.normal(size=T.shape)
    energy = np.clip(speaker_a + speaker_b + harmonics + noise_floor, 0, None)

    overlap = np.minimum(speaker_a, speaker_b)
    dominance_gap = np.abs(speaker_a - speaker_b)
    occlusion = 0.58 * energy + 1.35 * overlap - 0.28 * dominance_gap
    occlusion = np.clip(occlusion, 0, None)
    occlusion = occlusion / occlusion.max()

    fig = plt.figure(figsize=(14, 8.2), facecolor="#07111f")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#07111f")
    ax.set_position([0.06, 0.08, 0.78, 0.78])

    stride = 2
    surf = ax.plot_surface(
        T[::stride, ::stride],
        F[::stride, ::stride],
        occlusion[::stride, ::stride],
        cmap="turbo",
        linewidth=0,
        antialiased=True,
        alpha=0.96,
        shade=True,
    )

    # Decision contour ribbons on the floor.
    levels = [
        (0.26, "#2dd4bf", "mixed-safe"),
        (0.52, "#facc15", "separate-helpful"),
        (0.74, "#fb7185", "review-risk"),
    ]
    for level, color, _ in levels:
        ax.contour(
            T,
            F,
            occlusion,
            levels=[level],
            zdir="z",
            offset=-0.08,
            colors=[color],
            linewidths=2.4,
        )

    # A risk-guarded route trajectory across the landscape.
    route_t = np.linspace(0.08, 0.92, 85)
    route_f = 0.49 + 0.16 * np.sin(2 * np.pi * route_t + 0.5)
    ti = np.clip((route_t * (len(t) - 1)).astype(int), 0, len(t) - 1)
    fi = np.clip((route_f * (len(f) - 1)).astype(int), 0, len(f) - 1)
    route_z = occlusion[fi, ti] + 0.08
    ax.plot(
        route_t,
        route_f,
        route_z,
        color="white",
        linewidth=3.0,
        alpha=0.95,
        label="risk-guarded Stage-1 gate",
    )
    ax.scatter(
        route_t[::10],
        route_f[::10],
        route_z[::10],
        color="#ffffff",
        edgecolor="#0f172a",
        s=44,
        depthshade=False,
    )

    # A translucent wall marks the high-occlusion review zone.
    verts = [
        [(0.58, 0.0, -0.08), (0.58, 1.0, -0.08), (0.58, 1.0, 1.05), (0.58, 0.0, 1.05)]
    ]
    wall = Poly3DCollection(verts, facecolors="#fb7185", alpha=0.12, edgecolors="#fb7185")
    ax.add_collection3d(wall)

    ax.view_init(elev=31, azim=-57)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_zlim(-0.08, 1.08)
    ax.set_xlabel("Time", labelpad=10, color="white")
    ax.set_ylabel("Frequency band", labelpad=10, color="white")
    ax.set_zlabel("AudioDepth occlusion pressure", labelpad=12, color="white")
    ax.tick_params(colors="#cbd5e1")
    ax.xaxis.pane.set_facecolor((0.02, 0.05, 0.10, 0.9))
    ax.yaxis.pane.set_facecolor((0.02, 0.05, 0.10, 0.9))
    ax.zaxis.pane.set_facecolor((0.02, 0.05, 0.10, 0.9))
    ax.xaxis._axinfo["grid"]["color"] = (0.55, 0.65, 0.78, 0.22)
    ax.yaxis._axinfo["grid"]["color"] = (0.55, 0.65, 0.78, 0.22)
    ax.zaxis._axinfo["grid"]["color"] = (0.55, 0.65, 0.78, 0.22)

    fig.text(
        0.5,
        0.955,
        "AudioDepth as a 3D Time-Frequency Occlusion Landscape",
        color="white",
        fontsize=17,
        fontweight="bold",
        ha="center",
    )
    fig.text(
        0.5,
        0.918,
        "A conceptual pre-ASR view: overlapping speakers become colored acoustic ridges, and the white path marks a risk-guarded route.",
        color="#cbd5e1",
        fontsize=9.5,
        ha="center",
    )

    cbar = fig.colorbar(surf, ax=ax, shrink=0.58, pad=0.06)
    cbar.set_label("pre-ASR occlusion intensity", color="white")
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.get_yticklabels(), color="white")

    legend_handles = [
        plt.Line2D([0], [0], color="#2dd4bf", lw=3, label="mixed-safe contour"),
        plt.Line2D([0], [0], color="#facc15", lw=3, label="separate-helpful contour"),
        plt.Line2D([0], [0], color="#fb7185", lw=3, label="review-risk contour"),
        plt.Line2D([0], [0], color="white", lw=3, label="risk-guarded route"),
    ]
    leg = ax.legend(
        handles=legend_handles,
        loc="upper left",
        bbox_to_anchor=(0.02, 0.98),
        frameon=True,
        facecolor="#0f172a",
        edgecolor="#334155",
        labelcolor="white",
    )
    for text in leg.get_texts():
        text.set_color("white")

    fig.text(
        0.5,
        0.025,
        "Conceptual visualization generated from the AudioDepth study narrative; not a raw experiment dump.",
        ha="center",
        color="#cbd5e1",
        fontsize=9,
    )
    save(fig, "audio_depth_3d_occlusion_landscape", facecolor="#07111f")


def make_audio_depth_fields(
    seed: int = 11,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Create conceptual AudioDepth channels for documentation figures."""

    rng = np.random.default_rng(seed)
    t = np.linspace(0, 1, 220)
    f = np.linspace(0, 1, 150)
    T, F = np.meshgrid(t, f)

    speaker_a = (
        1.08 * np.exp(-((F - (0.30 + 0.07 * np.sin(7.5 * T))) ** 2) / 0.005)
        * (0.48 + 0.52 * np.sin(2 * np.pi * (2.0 * T + 0.1)) ** 2)
    )
    speaker_b = (
        0.96 * np.exp(-((F - (0.64 + 0.06 * np.cos(6.2 * T))) ** 2) / 0.007)
        * (0.46 + 0.54 * np.cos(2 * np.pi * (1.6 * T - 0.18)) ** 2)
    )
    texture = 0.16 * np.sin(17 * np.pi * F + 2.5 * np.cos(2 * np.pi * T)) ** 2
    noise = 0.035 * rng.normal(size=T.shape)

    log_mel = np.clip(speaker_a + speaker_b + texture + noise, 0, None)
    overlap = np.minimum(speaker_a, speaker_b)
    dominance = (speaker_a - speaker_b) / (speaker_a + speaker_b + 0.08)
    uncertainty = overlap * (1 - np.abs(dominance))

    for arr in (log_mel, overlap, dominance, uncertainty):
        arr -= arr.min()
        if arr.max() > 0:
            arr /= arr.max()

    return T, F, log_mel, overlap, uncertainty


def figure_audio_depth_channels() -> None:
    """Show the three deployable representation channels as a polished triptych."""

    _, _, log_mel, overlap, uncertainty = make_audio_depth_fields()
    panels = [
        ("Channel 1: mixed log-mel energy", log_mel, "magma"),
        ("Channel 2: overlap proxy", overlap, "viridis"),
        ("Channel 3: occlusion uncertainty", uncertainty, "turbo"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(14.2, 5.6), constrained_layout=True)
    fig.patch.set_facecolor("#08111f")
    fig.suptitle(
        "AudioDepth Representation: Three Pre-ASR Views of Overlap",
        color="white",
        fontsize=17,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.91,
        "A conceptual channel map: energy, overlap, and uncertainty expose acoustic risk before transcript instability appears.",
        color="#cbd5e1",
        ha="center",
        fontsize=9.5,
    )

    for ax, (title, data, cmap) in zip(axes, panels):
        ax.set_facecolor("#08111f")
        im = ax.imshow(
            data,
            origin="lower",
            aspect="auto",
            interpolation="bilinear",
            cmap=cmap,
            extent=[0, 1, 0, 1],
        )
        ax.set_title(title, color="white", fontsize=11, fontweight="bold", pad=10)
        ax.set_xlabel("Time", color="#e2e8f0")
        ax.set_ylabel("Frequency band", color="#e2e8f0")
        ax.tick_params(colors="#cbd5e1", labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("#475569")
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.025)
        cbar.ax.tick_params(colors="#cbd5e1", labelsize=7)
        cbar.outline.set_edgecolor("#64748b")

    fig.text(
        0.5,
        0.025,
        "Conceptual figure generated for explanation; not a raw dataset artifact.",
        ha="center",
        color="#cbd5e1",
        fontsize=9,
    )
    save(fig, "audio_depth_channel_triptych", facecolor="#08111f")


def figure_route_decision_space() -> None:
    """Render AudioDepth route choice as a colorful decision space."""

    rng = np.random.default_rng(23)
    n = 210
    overlap = rng.beta(2.1, 2.0, n)
    uncertainty = np.clip(0.12 + 0.75 * overlap + rng.normal(0, 0.14, n), 0, 1)
    text_instability = np.clip(
        0.16 + 0.55 * uncertainty + rng.normal(0, 0.16, n),
        0,
        1,
    )
    risk = 0.48 * overlap + 0.34 * uncertainty + 0.18 * text_instability

    labels = np.where(
        risk < 0.38,
        "mixed-safe",
        np.where(risk < 0.66, "separate-helpful", "review/fallback"),
    )
    colors = {
        "mixed-safe": "#2dd4bf",
        "separate-helpful": "#facc15",
        "review/fallback": "#fb7185",
    }
    sizes = 55 + 210 * text_instability

    fig, ax = plt.subplots(figsize=(11.8, 7.4), facecolor="#08111f")
    ax.set_facecolor("#08111f")

    x = np.linspace(0, 1, 180)
    y1 = np.clip(0.55 - 0.45 * x, 0, 1)
    y2 = np.clip(0.92 - 0.55 * x, 0, 1)
    ax.fill_between(x, 0, y1, color="#123b45", alpha=0.55, label="mixed-safe region")
    ax.fill_between(x, y1, y2, color="#51451a", alpha=0.48, label="separate-helpful region")
    ax.fill_between(x, y2, 1, color="#4a1f32", alpha=0.50, label="review/fallback region")
    ax.plot(x, y1, color="#2dd4bf", lw=2.4)
    ax.plot(x, y2, color="#fb7185", lw=2.4)

    for label in ("mixed-safe", "separate-helpful", "review/fallback"):
        mask = labels == label
        ax.scatter(
            overlap[mask],
            uncertainty[mask],
            s=sizes[mask],
            c=colors[label],
            edgecolor="#e2e8f0",
            linewidth=0.7,
            alpha=0.88,
            label=label,
        )

    path_x = np.linspace(0.12, 0.88, 9)
    path_y = np.clip(0.22 + 0.54 * path_x + 0.08 * np.sin(9 * path_x), 0, 1)
    ax.plot(path_x, path_y, color="white", lw=3.0, alpha=0.92)
    ax.scatter(path_x, path_y, s=74, c="white", edgecolor="#0f172a", zorder=5)
    ax.annotate(
        "risk-guarded route\nblocks unsafe direct bypass",
        xy=(path_x[-2], path_y[-2]),
        xytext=(0.55, 0.17),
        color="white",
        fontsize=10,
        arrowprops=dict(arrowstyle="->", color="white", lw=1.6),
        bbox=dict(boxstyle="round,pad=0.35", fc="#111827", ec="#475569"),
    )

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("AudioDepth overlap proxy", color="#e2e8f0", labelpad=10)
    ax.set_ylabel("Occlusion uncertainty", color="#e2e8f0", labelpad=10)
    ax.grid(True, color="#334155", alpha=0.45)
    ax.tick_params(colors="#cbd5e1")
    for spine in ax.spines.values():
        spine.set_color("#64748b")

    ax.set_title(
        "AudioDepth Route Decision Space",
        color="white",
        fontsize=17,
        fontweight="bold",
        pad=18,
    )
    ax.text(
        0.5,
        1.02,
        "Bubble size reflects transcript-instability pressure; color shows the route family.",
        transform=ax.transAxes,
        ha="center",
        color="#cbd5e1",
        fontsize=9.5,
    )
    leg = ax.legend(
        loc="upper left",
        frameon=True,
        facecolor="#0f172a",
        edgecolor="#334155",
        labelcolor="white",
    )
    for text in leg.get_texts():
        text.set_color("white")

    fig.text(
        0.5,
        0.025,
        "Conceptual route-space visualization: use as explanatory material, not as benchmark evidence.",
        ha="center",
        color="#cbd5e1",
        fontsize=9,
    )
    save(fig, "audio_depth_route_decision_space", facecolor="#08111f")


def main() -> None:
    setup()
    figure_3d_occlusion_landscape()
    figure_audio_depth_channels()
    figure_route_decision_space()
    print(f"Wrote figures to {OUT}")


if __name__ == "__main__":
    main()
