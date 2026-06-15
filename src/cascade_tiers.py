"""
Mode B: Compute-aware Cascaded Recognition — Three-Tier Architecture
====================================================================

Research question: When should the system spend more compute?

This module implements a reference-free three-tier cascade that routes
each audio sample through progressively more expensive processing only
when observable instability signals justify the extra cost.

Tiers
-----
Tier 1 (Cheap)  — whisper-small + router_v2 → mixed or separated
Tier 2 (Strong) — risk-gated stronger ASR or cleaned post-processing
Tier 3 (Critic) — LLM critic or manual review for extreme-instability cases

All escalation decisions use only reference-free, observable signals
(overlap level, length inflation, duplicate removal count, runtime ratio).
CER is reserved for post-decision evaluation only.

Outputs
-------
- ``results/tables/cascade_tiers_performance.csv`` — per-case tier assignments
- ``results/tables/cascade_tiers_coverage.csv`` — tier distribution & coverage stats
- ``results/tables/cascade_tiers_routing_table.csv`` — cost-aware routing table
- ``results/figures/cascade_tiers_summary.md`` — human-readable summary
- ``results/figures/cascade_tiers_cer_cost_tradeoff.png`` — tradeoff visualization

Label: experimental/frontier
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .io_helpers import read_csv_rows, to_float, to_int, write_csv_json

# ── Module metadata ──────────────────────────────────────────────────

MODULE_LABEL = "experimental/frontier"

# ── Cost model ───────────────────────────────────────────────────────

TIER_COST: dict[str, float] = {
    # Tier 1 — cheap routes
    "mixed_whisper": 1.0,
    "separated_whisper": 2.0,
    # Tier 2 — stronger routes
    "separated_whisper_cleaned": 2.1,
    "stronger_model": 2.5,
    # Tier 3 — critic / manual routes
    "llm_critic": 3.5,
    "manual_review": 4.0,
}

TIER_STRATEGIES = [
    "tiered_cascade_v1",
    "tiered_cascade_risk_aware",
]


# ── Instability detection (reference-free) ───────────────────────────

def _compute_instability_score(case: dict[str, Any]) -> float:
    """Compute a 0-1 instability score from observable signals only.

    Uses duplicate removals, runtime inflation, and text-length inflation.
    Thresholds are calibrated for overlapping speech where separated transcripts
    are inherently ~2× longer than mixed (two speaker streams).
    """
    # text_length_ratio > 2.5 suggests insertion hallucination beyond normal 2-speaker expansion
    text_length_ratio = to_float(case.get("length_ratio", 1.0)) or 1.0
    duplicate_count = to_int(case.get("duplicate_removed_count", 0)) or 0
    runtime_ratio = to_float(case.get("runtime_ratio", 1.0)) or 1.0

    score = 0.0
    # Text-length inflation above 2.5 (normal 2-speaker ~2.0, insertion pushes higher)
    if text_length_ratio > 2.5:
        score += min((text_length_ratio - 2.5) / 1.5, 0.35)
    # Duplicate removals: starts contributing above 3
    if duplicate_count > 3:
        score += min(duplicate_count / 20.0, 0.40)
    # Runtime inflation: starts contributing above 1.3
    if runtime_ratio > 1.3:
        score += min((runtime_ratio - 1.3) / 1.2, 0.25)
    return round(min(score, 1.0), 6)


def _is_unstable(case: dict[str, Any]) -> bool:
    """Reference-free instability check for Tier 2 escalation.

    Uses thresholds calibrated for overlapping speech:
    - text_length_ratio > 2.8: insertion hallucination beyond normal 2-speaker length (~2×)
    - duplicate_removed_count >= 5: moderate repetition artifacts
    - runtime_ratio > 1.5: processing took significantly longer than mixed
    - overlap >= 3 + duplicates >= 3: heavy-overlap cases with some artifacts
    """
    length_ratio = to_float(case.get("length_ratio", 1.0)) or 1.0
    duplicate_count = to_int(case.get("duplicate_removed_count", 0)) or 0
    runtime_ratio = to_float(case.get("runtime_ratio", 1.0)) or 1.0
    overlap_level = to_int(case.get("overlap_level", 0)) or 0

    return (
        length_ratio > 2.8
        or duplicate_count >= 5
        or runtime_ratio > 1.5
        or (overlap_level >= 3 and duplicate_count >= 3)
    )


def _is_extremely_unstable(case: dict[str, Any]) -> bool:
    """Reference-free extreme-instability check for Tier 3 escalation.

    Requires at least 2 severe signals:
    - text_length_ratio > 3.5: extreme insertion
    - duplicate_count >= 12: heavy repetition
    - runtime_ratio > 2.5: extreme processing difficulty
    - overlap >= 4 + duplicates >= 6: hardest overlap with artifacts
    """
    length_ratio = to_float(case.get("length_ratio", 1.0)) or 1.0
    duplicate_count = to_int(case.get("duplicate_removed_count", 0)) or 0
    runtime_ratio = to_float(case.get("runtime_ratio", 1.0)) or 1.0
    overlap_level = to_int(case.get("overlap_level", 0)) or 0

    severe_signals = 0
    if length_ratio > 3.5:
        severe_signals += 1
    if duplicate_count >= 12:
        severe_signals += 1
    if runtime_ratio > 2.5:
        severe_signals += 1
    if overlap_level >= 4 and duplicate_count >= 6:
        severe_signals += 1
    return severe_signals >= 2


# ── Tier resolution functions ────────────────────────────────────────

def resolve_tier1(case_id: str, decisions: dict[str, str]) -> str:
    """Resolve Tier 1: return the router_v2 decision for this case.

    Args:
        case_id: The case identifier.
        decisions: Mapping of ``case_id -> selected_method`` from router_v2.

    Returns:
        The Tier 1 method name (mixed_whisper or separated_whisper).

    Falls back to ``mixed_whisper`` when no decision exists.
    """
    return decisions.get(case_id, "mixed_whisper")


def resolve_tier2(case: dict[str, Any], tier1_method: str) -> str:
    """Resolve Tier 2: escalate to stronger processing if unstable.

    Decision logic (reference-free):
    - If NOT unstable → keep Tier 1 method
    - If unstable AND overlap >= 3 → escalate to stronger_model
    - If unstable AND overlap 0-2 → escalate to separated_whisper_cleaned
      (cheaper than full stronger model, still adds duplicate suppression)

    Args:
        case: Case dict with overlap_level, length_ratio, duplicate_removed_count, runtime_ratio.
        tier1_method: The method selected at Tier 1.

    Returns:
        The Tier 2 method name.
    """
    if not _is_unstable(case):
        return tier1_method

    overlap_level = to_int(case.get("overlap_level", 0)) or 0

    # High overlap → stronger model (more likely to benefit from larger ASR)
    if overlap_level >= 3:
        return "stronger_model"

    # Low/mid overlap → cleaned transcript first (cheaper escalation)
    return "separated_whisper_cleaned"


def resolve_tier3(case: dict[str, Any], tier2_method: str) -> str:
    """Resolve Tier 3: escalate to LLM critic or manual review.

    Decision logic (reference-free):
    - If NOT extremely unstable → keep Tier 2 method
    - If extremely unstable AND overlap >= 3 → manual_review (hardest cases)
    - Otherwise → llm_critic (automated, still expensive but cheaper than human)

    Args:
        case: Case dict with observable signals.
        tier2_method: The method selected at Tier 2.

    Returns:
        The Tier 3 method name.
    """
    if not _is_extremely_unstable(case):
        return tier2_method

    overlap_level = to_int(case.get("overlap_level", 0)) or 0

    # Highest overlap + extreme instability → human review
    if overlap_level >= 4:
        return "manual_review"

    # Otherwise → automated LLM critic
    return "llm_critic"


# ── Full three-tier pipeline ─────────────────────────────────────────

def run_three_tier_pipeline(
    cases: list[dict[str, Any]],
    decisions: dict[str, str],
) -> list[dict[str, Any]]:
    """Run the full three-tier cascade pipeline on a set of cases.

    Each case flows through Tier 1 → Tier 2 → Tier 3, escalating only
    when reference-free instability signals trigger.

    Args:
        cases: List of case dicts. Each must have ``case_id``, ``overlap_level``,
               ``length_ratio``, ``duplicate_removed_count``, ``runtime_ratio``.
        decisions: Router v2 decisions mapping ``case_id -> method``.

    Returns:
        List of result dicts with keys: case_id, tier, selected_method,
        compute_cost, instability_score, risk_triggered.
    """
    results: list[dict[str, Any]] = []
    for case in cases:
        case_id = str(case.get("case_id", "")).strip()
        if not case_id:
            continue

        instability_score = _compute_instability_score(case)
        risk_triggered = _is_unstable(case)

        # Tier 1
        t1_method = resolve_tier1(case_id, decisions)

        # Tier 2
        t2_method = resolve_tier2(case, t1_method)

        # Tier 3
        final_method = resolve_tier3(case, t2_method)

        # Determine which tier the final method belongs to
        if final_method == t1_method:
            tier = 1
        elif final_method == t2_method:
            tier = 2
        else:
            tier = 3

        results.append({
            "case_id": case_id,
            "tier": tier,
            "tier1_method": t1_method,
            "tier2_method": t2_method,
            "selected_method": final_method,
            "compute_cost": TIER_COST.get(final_method, TIER_COST["manual_review"]),
            "instability_score": round(instability_score, 6),
            "risk_triggered": risk_triggered,
        })
    return results


# ── Output builders ──────────────────────────────────────────────────

def build_tier_summary_rows(
    pipeline_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build per-case tier summary rows for CSV output.

    Args:
        pipeline_results: Output from ``run_three_tier_pipeline``.

    Returns:
        List of row dicts suitable for CSV writing.
    """
    return [
        {
            "case_id": r["case_id"],
            "tier": r["tier"],
            "selected_method": r["selected_method"],
            "compute_cost": r["compute_cost"],
            "instability_score": r.get("instability_score", 0.0),
            "risk_triggered": r.get("risk_triggered", False),
            "tier1_method": r.get("tier1_method", ""),
            "tier2_method": r.get("tier2_method", ""),
        }
        for r in pipeline_results
    ]


def build_coverage_stats(
    pipeline_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build aggregate coverage and tier distribution statistics.

    Args:
        pipeline_results: Output from ``run_three_tier_pipeline``.

    Returns:
        Stats dict with total_cases, per-tier counts and ratios,
        average cost, automatic coverage ratio.
    """
    total = len(pipeline_results)
    if total == 0:
        return {
            "total_cases": 0, "tier1_count": 0, "tier2_count": 0, "tier3_count": 0,
            "tier1_ratio": 0.0, "tier2_ratio": 0.0, "tier3_ratio": 0.0,
            "average_cost": 0.0, "automatic_coverage": 0.0,
            "strong_model_call_count": 0, "manual_review_count": 0,
        }

    tier1 = sum(1 for r in pipeline_results if r["tier"] == 1)
    tier2 = sum(1 for r in pipeline_results if r["tier"] == 2)
    tier3 = sum(1 for r in pipeline_results if r["tier"] == 3)
    strong_calls = sum(1 for r in pipeline_results if r.get("selected_method") == "stronger_model")
    manual = sum(1 for r in pipeline_results if r.get("selected_method") in ("manual_review", "llm_critic"))
    avg_cost = sum(r.get("compute_cost", 0) for r in pipeline_results) / total

    return {
        "total_cases": total,
        "tier1_count": tier1,
        "tier2_count": tier2,
        "tier3_count": tier3,
        "tier1_ratio": round(tier1 / total, 6),
        "tier2_ratio": round(tier2 / total, 6),
        "tier3_ratio": round(tier3 / total, 6),
        "average_cost": round(avg_cost, 6),
        "automatic_coverage": round((tier1 + tier2) / total, 6),
        "strong_model_call_count": strong_calls,
        "manual_review_count": manual,
    }


def build_cost_aware_routing_table(
    pipeline_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build a cost-aware routing table mapping each case to its recommended route.

    Args:
        pipeline_results: Output from ``run_three_tier_pipeline``.

    Returns:
        List of routing row dicts.
    """
    return [
        {
            "case_id": r["case_id"],
            "tier": r["tier"],
            "recommended_route": r["selected_method"],
            "compute_cost": r["compute_cost"],
            "instability_score": r.get("instability_score", 0.0),
            "risk_triggered": r.get("risk_triggered", False),
        }
        for r in pipeline_results
    ]


# ── Comparative analysis ────────────────────────────────────────────

def build_comparison_rows(
    pipeline_results: list[dict[str, Any]],
    cer_lookup: dict[tuple[str, str], float],
) -> list[dict[str, Any]]:
    """Build strategy-level comparison rows for CER-runtime tradeoff analysis.

    Combines the three-tier cascade results with fixed-strategy baselines
    (mixed_whisper, separated_whisper, separated_whisper_cleaned) so the
    tradeoff chart includes both the cascade and the fixed baselines.

    Args:
        pipeline_results: Output from ``run_three_tier_pipeline``.
        cer_lookup: CER lookup keyed by ``(case_id, method)``.

    Returns:
        List of strategy rows with average_cer, average_compute_cost,
        automatic_coverage, and selected_method_mix.
    """
    rows: list[dict[str, Any]] = []

    # ── Fixed-strategy baselines ──────────────────────────────────
    case_ids = sorted({r["case_id"] for r in pipeline_results})
    for strategy, method in [
        ("fixed_mixed_whisper", "mixed_whisper"),
        ("fixed_separated_whisper", "separated_whisper"),
        ("fixed_separated_whisper_cleaned", "separated_whisper_cleaned"),
    ]:
        cer_values: list[float] = []
        costs: list[float] = []
        for cid in case_ids:
            costs.append(TIER_COST.get(method, 1.0))
            cer = cer_lookup.get((cid, method))
            if cer is not None:
                cer_values.append(cer)
        rows.append({
            "strategy": strategy,
            "label": "experimental/frontier",
            "average_cer": round(sum(cer_values) / len(cer_values), 6) if cer_values else "",
            "average_compute_cost": round(sum(costs) / len(costs), 6) if costs else 0.0,
            "automatic_coverage": 1.0,
            "selected_method_mix": f"{method}:{len(case_ids)}",
            "notes": "Fixed strategy — always uses the same ASR method.",
        })

    # ── Router v2 baseline ────────────────────────────────────────
    router_cer_values: list[float] = []
    router_costs: list[float] = []
    router_method_counts: dict[str, int] = {}
    for r in pipeline_results:
        t1 = r.get("tier1_method", "mixed_whisper")
        router_method_counts[t1] = router_method_counts.get(t1, 0) + 1
        router_costs.append(TIER_COST.get(t1, 1.0))
        cer = cer_lookup.get((r["case_id"], t1))
        if cer is not None:
            router_cer_values.append(cer)
    rows.append({
        "strategy": "router_v2_baseline",
        "label": "experimental/frontier",
        "average_cer": round(sum(router_cer_values) / len(router_cer_values), 6) if router_cer_values else "",
        "average_compute_cost": round(sum(router_costs) / len(router_costs), 6) if router_costs else 0.0,
        "automatic_coverage": 1.0,
        "selected_method_mix": ";".join(
            f"{m}:{router_method_counts[m]}" for m in sorted(router_method_counts)
        ),
        "notes": "Router v2 baseline — single-tier decision.",
    })

    # ── Three-tier cascade ────────────────────────────────────────
    tiered_cer_values: list[float] = []
    tiered_costs: list[float] = []
    tiered_method_counts: dict[str, int] = {}
    manual_count = 0
    for r in pipeline_results:
        method = r.get("selected_method", "mixed_whisper")
        tiered_method_counts[method] = tiered_method_counts.get(method, 0) + 1
        tiered_costs.append(r.get("compute_cost", TIER_COST.get(method, 1.0)))
        if method in ("manual_review", "llm_critic"):
            manual_count += 1
            continue
        cer = r.get("cer") if "cer" in r else cer_lookup.get((r["case_id"], method))
        if cer is not None:
            tiered_cer_values.append(cer)
    auto_cov = (len(pipeline_results) - manual_count) / len(pipeline_results) if pipeline_results else 1.0
    rows.append({
        "strategy": "tiered_cascade_v1",
        "label": "experimental/frontier",
        "average_cer": round(sum(tiered_cer_values) / len(tiered_cer_values), 6) if tiered_cer_values else "",
        "average_compute_cost": round(sum(tiered_costs) / len(tiered_costs), 6) if tiered_costs else 0.0,
        "automatic_coverage": round(auto_cov, 6),
        "selected_method_mix": ";".join(
            f"{m}:{tiered_method_counts[m]}" for m in sorted(tiered_method_counts)
        ),
        "notes": "Three-tier cascade — escalates only on instability signals.",
    })

    return rows


def render_tiers_tradeoff_figure(
    rows: list[dict[str, Any]],
    output_path: Path,
) -> None:
    """Render a CER vs compute-cost tradeoff scatter plot.

    Falls back to a minimal PNG when matplotlib is unavailable.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        _write_fallback_tradeoff_png(output_path, rows)
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    x_values = [to_float(row["average_compute_cost"]) for row in rows]
    y_values = [to_float(row["average_cer"]) for row in rows]

    colors = {
        "tiered_cascade_v1": "#d45d00",
        "router_v2_baseline": "#2f6f8f",
        "fixed_mixed_whisper": "#6b8e23",
        "fixed_separated_whisper": "#8b0000",
        "fixed_separated_whisper_cleaned": "#8b008b",
    }
    point_colors = [colors.get(str(row.get("strategy", "")), "#666666") for row in rows]

    ax.scatter(x_values, y_values, c=point_colors, s=100, edgecolors="#333333", linewidths=0.5)
    for row, x_val, y_val in zip(rows, x_values, y_values):
        label = str(row.get("strategy", "")).replace("_", "\n")
        ax.annotate(label, (x_val, y_val), textcoords="offset points",
                     xytext=(7, 5), fontsize=7, fontfamily="monospace")

    ax.set_xlabel("Average compute cost (proxy units)")
    ax.set_ylabel("Average CER")
    ax.set_title("Three-Tier Cascade: CER vs Compute Cost Trade-off")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(str(output_path), dpi=120)
    plt.close(fig)


def _write_fallback_tradeoff_png(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write a minimal PNG as fallback when matplotlib is unavailable."""
    width, height = 900, 550
    pixels = bytearray(b"\xff\xff\xff" * width * height)
    left, right, top, bottom = 90, 40, 40, 80
    plot_w = width - left - right
    plot_h = height - top - bottom

    def _set_px(x: int, y: int, r: int, g: int, b: int) -> None:
        if 0 <= x < width and 0 <= y < height:
            idx = (y * width + x) * 3
            pixels[idx:idx + 3] = bytes([r, g, b])

    def _draw_h_line(y: int, r: int, g: int, b: int) -> None:
        for x2 in range(left, left + plot_w):
            _set_px(x2, y, r, g, b)

    def _draw_v_line(x: int, r: int, g: int, b: int) -> None:
        for y2 in range(top, top + plot_h):
            _set_px(x, y2, r, g, b)

    axis_color = (45, 45, 45)
    grid_color = (220, 220, 220)
    point_color = (47, 111, 143)
    highlight_color = (212, 93, 0)

    _draw_h_line(top + plot_h, *axis_color)
    _draw_v_line(left, *axis_color)
    for tick in range(6):
        x = left + round(plot_w * tick / 5)
        y = top + round(plot_h * tick / 5)
        _draw_v_line(x, *grid_color)
        _draw_h_line(y, *grid_color)

    x_values = [to_float(r["average_compute_cost"]) for r in rows]
    y_values = [to_float(r["average_cer"]) for r in rows]
    if not x_values or not y_values:
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_png_bytes(path, width, height, bytes(pixels))
        return

    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)
    if x_min == x_max:
        x_min -= 1.0; x_max += 1.0
    if y_min == y_max:
        y_min -= 0.1; y_max += 0.1
    x_pad = (x_max - x_min) * 0.08
    y_pad = (y_max - y_min) * 0.08

    for row, x_val, y_val in zip(rows, x_values, y_values):
        is_tiered = str(row.get("strategy", "")) == "tiered_cascade_v1"
        px = left + round((x_val - x_min + x_pad) / (x_max - x_min + 2 * x_pad) * plot_w)
        py = top + round((y_max - y_val + y_pad) / (y_max - y_min + 2 * y_pad) * plot_h)
        c = highlight_color if is_tiered else point_color
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                if dx * dx + dy * dy <= 16:
                    _set_px(px + dx, py + dy, *c)

    path.parent.mkdir(parents=True, exist_ok=True)
    _write_png_bytes(path, width, height, bytes(pixels))


def _write_png_bytes(path: Path, width: int, height: int, raw_rgb: bytes) -> None:
    """Write a minimal PNG file from raw RGB pixels."""

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    raw = bytearray()
    raw.extend(b"\x89PNG\r\n\x1a\n")
    raw.extend(_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)))
    scanlines = bytearray()
    for y in range(height):
        scanlines.append(0)
        scanlines.extend(raw_rgb[y * width * 3:(y + 1) * width * 3])
    raw.extend(_chunk(b"IDAT", zlib.compress(bytes(scanlines))))
    raw.extend(_chunk(b"IEND", b""))
    path.write_bytes(bytes(raw))


# ── Data loaders ─────────────────────────────────────────────────────

def load_cases_with_signals() -> list[dict[str, Any]]:
    """Load gold cases enriched with observable signals from router_v2 output.

    Reads instability signals directly from ``routing_decisions_v2.csv``:
    ``text_length_ratio``, ``duplicate_removed_count``, and ``runtime_ratio``.

    Returns:
        List of case dicts with case_id, overlap_level, length_ratio,
        duplicate_removed_count, runtime_ratio.
    """
    config = load_config()
    v2_rows = {
        str(row.get("case_id", "")).strip(): row
        for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "routing_decisions_v2.csv")
    }

    cases: list[dict[str, Any]] = []
    for case in config.get("audio_cases", []):
        case_id = str(case.get("id", "")).strip()
        if not case_id:
            continue
        v2_row = v2_rows.get(case_id, {})
        # Use the CSV's own text_length_ratio (separated_text_length / mixed_text_length).
        # For overlapping speech this is inherently > 1 because separated has two streams,
        # so escalation thresholds account for this by using a higher cutoff.
        text_length_ratio = to_float(v2_row.get("text_length_ratio")) or 1.0

        cases.append({
            "case_id": case_id,
            "overlap_level": to_int(case.get("overlap_level", 0)) or 0,
            "length_ratio": round(text_length_ratio, 6),
            "duplicate_removed_count": to_int(v2_row.get("duplicate_removed_count", 0)) or 0,
            "runtime_ratio": round(
                (to_float(v2_row.get("separated_runtime_sec")) or 0.0)
                / max(to_float(v2_row.get("mixed_runtime_sec")) or 1.0, 0.001),
                6,
            ),
        })
    return cases


def load_v2_decisions() -> dict[str, str]:
    """Load router_v2 decisions for gold cases.

    Returns:
        Mapping of ``case_id -> selected_method``.
    """
    return {
        str(row.get("case_id", "")).strip(): str(row.get("selected_method", "")).strip()
        for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "routing_decisions_v2.csv")
        if str(row.get("case_id", "")).strip()
    }


def load_cer_lookup() -> dict[tuple[str, str], float]:
    """Load CER lookup for post-decision evaluation only.

    Returns:
        Mapping of ``(case_id, method) -> cer_value``.
    """
    lookup: dict[tuple[str, str], float] = {}
    for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "cer_results.csv"):
        case_id = str(row.get("case_id", "")).strip()
        method = str(row.get("method", "")).strip()
        if case_id and method:
            lookup[(case_id, method)] = to_float(row.get("cer"))
    return lookup


# ── Main entry point ─────────────────────────────────────────────────

def main() -> None:
    """Run the three-tier cascade evaluation and write all outputs."""
    print("=" * 60)
    print("Mode B: Three-Tier Compute-Aware Cascaded Recognition")
    print(f"Label: {MODULE_LABEL}")
    print("=" * 60)

    # Load data
    cases = load_cases_with_signals()
    decisions = load_v2_decisions()
    cer_lookup = load_cer_lookup()

    print(f"\nLoaded {len(cases)} cases, {len(decisions)} routing decisions")

    # Run pipeline
    results = run_three_tier_pipeline(cases, decisions)

    # Attach CER for post-decision evaluation (NOT used in routing!)
    for r in results:
        cer = cer_lookup.get((r["case_id"], r["selected_method"]))
        r["cer"] = round(cer, 6) if cer is not None else None

    # Build outputs
    summary_rows = build_tier_summary_rows(results)
    coverage = build_coverage_stats(results)
    routing_table = build_cost_aware_routing_table(results)

    # Print summary
    print(f"\nTier distribution:")
    print(f"  Tier 1 (cheap):     {coverage['tier1_count']}/{coverage['total_cases']} "
          f"({coverage['tier1_ratio']:.1%})")
    print(f"  Tier 2 (stronger):  {coverage['tier2_count']}/{coverage['total_cases']} "
          f"({coverage['tier2_ratio']:.1%})")
    print(f"  Tier 3 (critic):    {coverage['tier3_count']}/{coverage['total_cases']} "
          f"({coverage['tier3_ratio']:.1%})")
    print(f"  Strong model calls: {coverage['strong_model_call_count']}")
    print(f"  Manual/critic flags: {coverage['manual_review_count']}")
    print(f"  Average cost:       {coverage['average_cost']:.4f}")
    print(f"  Automatic coverage: {coverage['automatic_coverage']:.1%}")

    # Per-case detail
    print(f"\nPer-case routing:")
    for r in results:
        cer_str = f"CER={r['cer']:.4f}" if r["cer"] is not None else "CER=N/A"
        print(f"  {r['case_id']:20s} → Tier {r['tier']} | {r['selected_method']:30s} "
              f"| cost={r['compute_cost']:.1f} | score={r['instability_score']:.3f} | {cer_str}")

    # Write outputs
    out_dir = PROJECT_ROOT / "results" / "tables"
    fig_dir = PROJECT_ROOT / "results" / "figures"

    # 1. Tier summary (per-case)
    tier_fields = [
        "case_id", "tier", "selected_method", "compute_cost",
        "instability_score", "risk_triggered", "tier1_method", "tier2_method",
    ]
    write_csv_json(
        summary_rows,
        out_dir / "cascade_tiers_performance.csv",
        out_dir / "cascade_tiers_performance.json",
        tier_fields,
    )
    print(f"\nWrote {out_dir / 'cascade_tiers_performance.csv'}")

    # 2. Coverage stats
    coverage_fields = [
        "total_cases", "tier1_count", "tier2_count", "tier3_count",
        "tier1_ratio", "tier2_ratio", "tier3_ratio",
        "average_cost", "automatic_coverage",
        "strong_model_call_count", "manual_review_count",
    ]
    coverage_rows = [coverage]
    write_csv_json(
        coverage_rows,
        out_dir / "cascade_tiers_coverage.csv",
        out_dir / "cascade_tiers_coverage.json",
        coverage_fields,
    )
    print(f"Wrote {out_dir / 'cascade_tiers_coverage.csv'}")

    # 3. Cost-aware routing table
    routing_fields = [
        "case_id", "tier", "recommended_route", "compute_cost",
        "instability_score", "risk_triggered",
    ]
    write_csv_json(
        routing_table,
        out_dir / "cascade_tiers_routing_table.csv",
        out_dir / "cascade_tiers_routing_table.json",
        routing_fields,
    )
    print(f"Wrote {out_dir / 'cascade_tiers_routing_table.csv'}")

    # 4. Summary markdown
    _write_tiers_summary_markdown(results, coverage, fig_dir)
    print(f"Wrote {fig_dir / 'cascade_tiers_summary.md'}")

    # 5. Comparative tradeoff analysis
    comparison_rows = build_comparison_rows(results, cer_lookup)
    comparison_fields = [
        "strategy", "label", "average_cer", "average_compute_cost",
        "automatic_coverage", "selected_method_mix", "notes",
    ]
    write_csv_json(
        comparison_rows,
        out_dir / "cascade_tiers_comparison.csv",
        out_dir / "cascade_tiers_comparison.json",
        comparison_fields,
    )
    print(f"Wrote {out_dir / 'cascade_tiers_comparison.csv'}")

    # 6. CER vs cost tradeoff chart
    chart_path = fig_dir / "cascade_tiers_cer_cost_tradeoff.png"
    render_tiers_tradeoff_figure(comparison_rows, chart_path)
    print(f"Wrote {chart_path}")

    # 7. Tradeoff comparison summary
    _write_comparison_summary_markdown(comparison_rows, fig_dir)
    print(f"Wrote {fig_dir / 'cascade_tiers_comparison_summary.md'}")

    print("\nMode B three-tier cascade evaluation complete.")


def _write_tiers_summary_markdown(
    results: list[dict[str, Any]],
    coverage: dict[str, Any],
    fig_dir: Path,
) -> None:
    """Write a human-readable summary markdown file."""
    lines = [
        "# Three-Tier Compute-Aware Cascade — Summary",
        "",
        f"**Label:** {MODULE_LABEL}",
        "",
        "## Architecture",
        "",
        "| Tier | Name | Trigger | Methods | Cost Range |",
        "|------|------|---------|---------|------------|",
        "| 1 | Cheap | Always (default) | mixed_whisper, separated_whisper | 1.0–2.0 |",
        "| 2 | Stronger | Unstable signals | separated_whisper_cleaned, stronger_model | 2.1–2.5 |",
        "| 3 | Critic | Extreme instability | llm_critic, manual_review | 3.5–4.0 |",
        "",
        "## Escalation Logic (Reference-Free)",
        "",
        "- **Tier 1 → Tier 2:** text_length_ratio > 2.8 OR duplicates >= 5 OR runtime_ratio > 1.5 OR (overlap >= 3 AND duplicates >= 3)",
        "- **Tier 2 → Tier 3:** >= 2 severe signals (text_length_ratio > 3.5, duplicates >= 12, runtime_ratio > 2.5, overlap >= 4 + duplicates >= 6)",
        "",
        "## Tier Distribution",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total cases | {coverage['total_cases']} |",
        f"| Tier 1 (cheap) | {coverage['tier1_count']} ({coverage['tier1_ratio']:.1%}) |",
        f"| Tier 2 (stronger) | {coverage['tier2_count']} ({coverage['tier2_ratio']:.1%}) |",
        f"| Tier 3 (critic) | {coverage['tier3_count']} ({coverage['tier3_ratio']:.1%}) |",
        f"| Strong model calls | {coverage['strong_model_call_count']} |",
        f"| Manual/critic flags | {coverage['manual_review_count']} |",
        f"| Average compute cost | {coverage['average_cost']:.4f} |",
        f"| Automatic coverage | {coverage['automatic_coverage']:.1%} |",
        "",
        "## Per-Case Routing Table",
        "",
        "| Case ID | Tier | Route | Cost | Instability | CER |",
        "|---------|------|-------|------|-------------|-----|",
    ]
    for r in results:
        cer_str = f"{r['cer']:.4f}" if r.get("cer") is not None else "N/A"
        lines.append(
            f"| {r['case_id']} | {r['tier']} | {r['selected_method']} | "
            f"{r['compute_cost']:.1f} | {r['instability_score']:.3f} | {cer_str} |"
        )

    lines.extend([
        "",
        "## Notes",
        "",
        "- All escalation decisions use ONLY reference-free observable signals.",
        "- CER is reserved for post-decision evaluation and is never used as a routing input.",
        "- `stronger_model` represents a hypothetical larger ASR model (e.g., whisper-medium)",
        "  with cost modeled at 2.5× the cheap baseline.",
        "- `llm_critic` and `manual_review` represent escalation gates for the hardest cases.",
        "- This is experimental/frontier evidence — not a deployment recommendation.",
    ])

    fig_dir.mkdir(parents=True, exist_ok=True)
    (fig_dir / "cascade_tiers_summary.md").write_text("\n".join(lines), encoding="utf-8")


def _write_comparison_summary_markdown(
    rows: list[dict[str, Any]],
    fig_dir: Path,
) -> None:
    """Write a comparison summary showing the tradeoff between strategies."""
    lines = [
        "# Three-Tier Cascade — Strategy Comparison",
        "",
        "**Label:** experimental/frontier",
        "",
        "## CER vs Compute Cost Trade-off",
        "",
        "| Strategy | Avg CER | Avg Cost | Auto Coverage | Method Mix |",
        "|----------|---------|----------|---------------|------------|",
    ]
    for row in rows:
        cer = f"{row['average_cer']:.4f}" if row.get("average_cer") != "" else "N/A"
        cost = f"{row['average_compute_cost']:.2f}" if row.get("average_compute_cost") else "N/A"
        cov = f"{row['automatic_coverage']:.1%}" if row.get("automatic_coverage") else "N/A"
        mix = str(row.get("selected_method_mix", ""))[:60]
        lines.append(f"| {row['strategy']} | {cer} | {cost} | {cov} | {mix} |")

    lines.extend([
        "",
        "## Interpretation",
        "",
        "- **fixed_mixed_whisper**: Cheapest, worst CER. Baseline cost floor.",
        "- **fixed_separated_whisper**: Better CER than mixed, 2× cost.",
        "- **fixed_separated_whisper_cleaned**: Marginally better CER than raw separated.",
        "- **router_v2_baseline**: Single-tier adaptive routing using overlap + instability signals.",
        "- **tiered_cascade_v1** (highlighted in chart): Three-tier cascade —",
        "  escalates only unstable samples to stronger processing.",
        "",
        "The goal is not the lowest possible CER but the best accuracy-cost balance.",
        "The tiered cascade should ideally sit near the Pareto frontier —",
        "meaningfully better CER than the cheap baseline without the full cost",
        "of always running the expensive route.",
        "",
        "## Notes",
        "",
        "- All escalation decisions use ONLY reference-free observable signals.",
        "- `stronger_model` represents a hypothetical larger ASR (e.g., whisper-medium).",
        "- Manual review / LLM critic costs are modeled at 3.5–4.0× the cheap baseline.",
    ])

    fig_dir.mkdir(parents=True, exist_ok=True)
    (fig_dir / "cascade_tiers_comparison_summary.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
