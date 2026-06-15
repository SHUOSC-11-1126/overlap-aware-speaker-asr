from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from .audio_depth_router_common import PROJECT_ROOT, best_route_from_cers, draw_bar_chart, read_csv, rel, write_csv
from .audio_depth_systematic_common import STRESS_CER_CSV, STRESS_LABELS_CSV, STRESS_MANIFEST_CSV, SYSTEMATIC_FIGURE_PREFIX, draw_simple_line, safe_float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate AudioDepth stress benchmark routes with labeled proxy CER.")
    parser.add_argument("--sample-limit", type=int, default=80)
    return parser.parse_args()


def proxy_cers(row: dict[str, str]) -> dict[str, float]:
    ratio = safe_float(row.get("overlap_ratio"), 0.0)
    dominance_gap = abs(safe_float(row.get("speaker_a_gain"), 1.0) - safe_float(row.get("speaker_b_gain"), 1.0))
    duration = safe_float(row.get("duration_sec"), 10.0)
    duration_penalty = 0.02 if duration > 20 else 0.01 if duration > 10 else 0.0
    style = row.get("interruption_style", "")
    style_penalty = {
        "clean_turn_taking": -0.04,
        "short_backchannel_overlap": 0.0,
        "medium_overlap": 0.03,
        "heavy_continuous_overlap": 0.08,
        "opposite_position_debate": 0.1,
    }.get(style, 0.0)
    mixed = 0.08 + 0.58 * ratio + 0.08 * dominance_gap + style_penalty + duration_penalty
    separated = 0.18 + 0.2 * max(0.0, 0.35 - ratio) + 0.18 * max(0.0, ratio - 0.78) + 0.04 * dominance_gap
    cleaned = separated + 0.04 - 0.22 * max(0.0, 0.35 - ratio) + 0.05 * max(0.0, ratio - 0.82)
    if ratio == 0:
        separated += 0.08 + 0.35 * dominance_gap
        cleaned = min(cleaned + 0.05, separated)
    return {
        "mixed_cer": round(max(0.0, mixed), 6),
        "separated_cer": round(max(0.0, separated), 6),
        "cleaned_cer": round(max(0.0, cleaned), 6),
    }


def aggregate_by_overlap(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["overlap_ratio"])].append(row)
    output = []
    for ratio, bucket in sorted(grouped.items(), key=lambda item: float(item[0])):
        output.append(
            {
                "overlap_ratio": ratio,
                "mixed_cer": round(float(np.mean([safe_float(row["mixed_cer"]) for row in bucket])), 6),
                "separated_cer": round(float(np.mean([safe_float(row["separated_cer"]) for row in bucket])), 6),
                "cleaned_cer": round(float(np.mean([safe_float(row["cleaned_cer"]) for row in bucket])), 6),
                "separation_delta_cer": round(float(np.mean([safe_float(row["separated_cer"]) - safe_float(row["mixed_cer"]) for row in bucket])), 6),
                "sample_count": len(bucket),
                "best_route_distribution": ",".join(f"{label}:{sum(1 for row in bucket if row['best_route_label'] == label)}" for label in ["mixed", "separated", "cleaned"]),
            }
        )
    return output


def main() -> None:
    args = parse_args()
    manifest = read_csv(STRESS_MANIFEST_CSV)
    if args.sample_limit:
        manifest = manifest[: args.sample_limit]
    cer_rows = []
    label_rows = []
    for row in manifest:
        cers = proxy_cers(row)
        merged = {
            "sample_id": row["sample_id"],
            "split": row["split"],
            "overlap_ratio": row["overlap_ratio"],
            "overlap_percent": row["overlap_percent"],
            "dominance_condition": row["dominance_condition"],
            "duration_bucket": row["duration_bucket"],
            "interruption_style": row["interruption_style"],
            **cers,
            "separation_delta_cer": round(cers["separated_cer"] - cers["mixed_cer"], 6),
            "evidence_type": "synthetic/silver_proxy",
            "notes": "Proxy CER generated because Whisper is unavailable in this environment; do not treat as real ASR CER.",
        }
        merged["best_route_label"] = best_route_from_cers(merged)
        cer_rows.append(merged)
        label_rows.append(
            {
                "sample_id": row["sample_id"],
                "split": row["split"],
                "overlap_ratio": row["overlap_ratio"],
                "best_route_label": merged["best_route_label"],
                "mixed_cer": merged["mixed_cer"],
                "separated_cer": merged["separated_cer"],
                "cleaned_cer": merged["cleaned_cer"],
                "label_source": "stress_proxy_cer_argmin",
                "evidence_type": "synthetic/silver_proxy",
            }
        )
    write_csv(STRESS_CER_CSV, cer_rows)
    write_csv(STRESS_LABELS_CSV, label_rows)
    by_overlap = aggregate_by_overlap(cer_rows)
    write_csv(PROJECT_ROOT / "results" / "tables" / "audio_depth_systematic_stress_by_overlap.csv", by_overlap)
    draw_bar_chart(
        by_overlap,
        SYSTEMATIC_FIGURE_PREFIX / "audio_depth_systematic_stress_cer_by_overlap.png",
        "overlap_ratio",
        "mixed_cer",
        "Stress benchmark mixed CER by overlap",
    )
    draw_simple_line(
        by_overlap,
        SYSTEMATIC_FIGURE_PREFIX / "audio_depth_systematic_separation_gain_curve.png",
        "overlap_ratio",
        "separation_delta_cer",
        "Separation gain curve: separated CER minus mixed CER",
    )
    print(f"Wrote {len(cer_rows)} proxy route evaluations to {rel(STRESS_CER_CSV)}")


if __name__ == "__main__":
    main()
