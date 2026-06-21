from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from .generative_audiodepth_common import (
    ANALYSIS_MAP_METADATA,
    BALANCED_COMPARISON,
    BALANCED_PREDICTIONS,
    CONTROLLED_V2_CER,
    CONTROLLED_V2_FILTERED,
    CONTROLLED_V2_MANIFEST,
    DATASET_CSV,
    DEPLOYABLE_MAP_METADATA,
    FIGURE_DIR,
    QUALITY_CSV,
    SAFETY_AUDIT,
    STAGE2_GUARD,
    TASKS,
    VECTOR_TASKS,
    dataset_fieldnames,
    load_npy,
    min_route_cer,
    normalize01,
    oracle_route,
    read_rows,
    review_needed,
    route_regrets,
    rows_by_sample,
    safe_float,
    save_target_array,
    unique_samples,
    write_csv,
    write_dataset,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build promptable Generative AudioDepth target dataset.")
    parser.add_argument("--limit", type=int, default=0, help="Optional sample limit for quick dry runs.")
    return parser.parse_args()


def uncertainty_from_teacher_map(arr: np.ndarray) -> np.ndarray:
    overlap = normalize01(arr[1])
    dominance = normalize01(arr[2])
    grad_t = np.abs(np.diff(overlap, axis=1, prepend=overlap[:, :1]))
    grad_f = np.abs(np.diff(overlap, axis=0, prepend=overlap[:1, :]))
    conflict = overlap * (1.0 - np.abs(dominance - 0.5) * 2.0)
    return normalize01(0.45 * conflict + 0.35 * grad_t + 0.20 * grad_f)


def task_target(sample: dict[str, Any], task: str, analysis_arr: np.ndarray) -> tuple[np.ndarray, str, str]:
    if task == "OVERLAP_MAP":
        return normalize01(analysis_arr[1]), "oracle_source_activity", "time_frequency_map"
    if task == "DOMINANCE_MAP":
        return normalize01(analysis_arr[2]), "oracle_source_activity", "time_frequency_map"
    if task == "UNCERTAINTY_MAP":
        return uncertainty_from_teacher_map(analysis_arr), "weak_uncertainty_target", "time_frequency_map"
    regrets = route_regrets(sample)
    if task == "ROUTE_REGRET":
        return (
            np.asarray([regrets["mixed"], regrets["separated"], regrets["cleaned"]], dtype=np.float32),
            "real_whisper_sample_level_regret",
            "sample_level_vector",
        )
    if task == "REVIEW_RISK":
        mixed_high = 1.0 if safe_float(sample.get("mixed_cer")) >= 0.6 else 0.0
        all_high = 1.0 if min_route_cer(sample) >= 0.6 else 0.0
        review = 1.0 if review_needed(sample) else 0.0
        return np.asarray([review, all_high, mixed_high], dtype=np.float32), "stage2_review_guard_heuristic", "sample_level_vector"
    raise ValueError(f"Unknown task: {task}")


def build_rows(limit: int = 0) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    manifest = rows_by_sample(CONTROLLED_V2_MANIFEST)
    cer = rows_by_sample(CONTROLLED_V2_CER)
    filtered = rows_by_sample(CONTROLLED_V2_FILTERED)
    analysis_meta = rows_by_sample(ANALYSIS_MAP_METADATA)
    deployable_meta = {
        row["sample_id"]: row
        for row in read_rows(DEPLOYABLE_MAP_METADATA)
        if row.get("source") == "controlled_v2" and row.get("sample_id")
    }
    usable_ids = [
        sample_id
        for sample_id in sorted(manifest)
        if sample_id in cer and sample_id in analysis_meta and sample_id in deployable_meta
    ]
    if limit:
        usable_ids = usable_ids[:limit]

    rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    for sample_id in usable_ids:
        m = manifest[sample_id]
        c = {**cer[sample_id], **filtered.get(sample_id, {})}
        d = deployable_meta[sample_id]
        a = analysis_meta[sample_id]
        sample = {**m, **c}
        sample["oracle_route"] = oracle_route(sample)
        regrets = route_regrets(sample)
        analysis_arr = load_npy(a["map_path"])
        base = {
            "sample_id": sample_id,
            "dataset_source": "controlled_route_sensitive_v2_real_whisper",
            "split_hint": m.get("split", ""),
            "mixed_wav_path": m.get("mixed_path", ""),
            "source_track_1_path": m.get("spk1_path", ""),
            "source_track_2_path": m.get("spk2_path", ""),
            "deployable_map_path": d.get("map_path", ""),
            "analysis_teacher_map_path": a.get("map_path", ""),
            "reference_type": m.get("reference_type", c.get("reference_type", "")),
            "overlap_ratio": m.get("overlap_ratio", c.get("overlap_ratio", "")),
            "dominance_type": m.get("dominance_type", ""),
            "target_family": m.get("intended_family", c.get("intended_family", "")),
            "oracle_route": sample["oracle_route"],
            "route_gap": c.get("route_gap", ""),
            "mixed_cer": c.get("mixed_cer", ""),
            "separated_cer": c.get("separated_cer", ""),
            "cleaned_cer": c.get("cleaned_cer", ""),
            "mixed_regret": regrets["mixed"],
            "separated_regret": regrets["separated"],
            "cleaned_regret": regrets["cleaned"],
            "review_needed": str(review_needed(sample)),
            "source_utterance_ids": m.get("source_utterance_ids", ""),
            "counterfactual_family_id": m.get("candidate_id", sample_id),
            "student_input_policy": "mixed_audio_or_mixed_logmel_only",
        }
        for key in [
            "logmel_mean",
            "logmel_std",
            "logmel_p90",
            "overlap_proxy_mean",
            "overlap_proxy_std",
            "overlap_proxy_p90",
            "uncertainty_proxy_mean",
            "uncertainty_proxy_std",
            "uncertainty_proxy_p90",
            "overlap_uncertainty_product",
        ]:
            base[key] = d.get(key, "")
        for task in TASKS:
            target, quality, scope = task_target(sample, task, analysis_arr)
            target_path = save_target_array(sample_id, task, target)
            row = {
                **base,
                "target_task": task,
                "target_path": target_path,
                "target_quality": quality,
                "target_scope": scope,
            }
            rows.append(row)
            quality_rows.append(
                {
                    "sample_id": sample_id,
                    "target_task": task,
                    "target_quality": quality,
                    "target_scope": scope,
                    "uses_source_tracks_for_teacher": str(task not in VECTOR_TASKS),
                    "student_input_policy": "mixed_audio_or_mixed_logmel_only",
                    "leakage_note": "teacher map may use source tracks; deployable student inputs do not",
                }
            )
    audit = {
        "controlled_v2_manifest_rows": len(manifest),
        "controlled_v2_real_whisper_cer_rows": len(cer),
        "analysis_teacher_map_rows": len(analysis_meta),
        "deployable_audiodepth_v2_rows": len(deployable_meta),
        "usable_samples": len(usable_ids),
        "dataset_rows": len(rows),
        "tasks": TASKS,
        "families": dict(Counter(row["target_family"] for row in rows if row["target_task"] == "ROUTE_REGRET")),
        "target_quality": dict(Counter(row["target_quality"] for row in rows)),
        "stage2_guard_available": STAGE2_GUARD.exists(),
        "safety_audit_available": SAFETY_AUDIT.exists(),
        "balanced_predictions_available": BALANCED_PREDICTIONS.exists(),
        "balanced_comparison_available": BALANCED_COMPARISON.exists(),
    }
    return rows, quality_rows, audit


def write_repo_audit(audit: dict[str, Any]) -> None:
    lines = [
        "# Generative AudioDepth Repo Input Audit",
        "",
        "Stage 32 starts from the actual `frontier/audio-depth-router` branch state, not from assumed paths.",
        "",
        "## Available Data Sources",
        "",
        f"- controlled_v2 manifest rows: {audit['controlled_v2_manifest_rows']}",
        f"- controlled_v2 real Whisper CER rows: {audit['controlled_v2_real_whisper_cer_rows']}",
        f"- analysis-only AudioDepth teacher map rows: {audit['analysis_teacher_map_rows']}",
        f"- deployable mixed-only AudioDepth v2 rows: {audit['deployable_audiodepth_v2_rows']}",
        f"- usable paired samples for this first promptable dataset: {audit['usable_samples']}",
        "",
        "## Teacher Labels",
        "",
        "- OVERLAP_MAP and DOMINANCE_MAP use source-track-derived analysis maps.",
        "- UNCERTAINTY_MAP is a weak map derived from teacher overlap structure and boundary gradients.",
        "- ROUTE_REGRET uses sample-level real-Whisper CER regret vectors.",
        "- REVIEW_RISK uses Stage-2-style review heuristics: small route gap, high minimum CER, or review-needed family.",
        "",
        "## Mixed-only Features",
        "",
        "- Deployable AudioDepth v2 metadata provides mixed-logmel, overlap proxy, uncertainty proxy, and summary statistics.",
        "- Student/deployable paths are restricted to mixed audio or mixed-logmel-derived maps.",
        "",
        "## Missing or Limited Fields",
        "",
        "- No reliable window-level CER exists, so route regret remains sample-level.",
        "- Speaker IDs are not separately available beyond source utterance IDs.",
        "- Teacher maps are controlled/silver-plus analysis targets, not production labels.",
        "",
        "## Leakage Risks",
        "",
        "- Source tracks are allowed only for teacher-target construction.",
        "- Student inference must not accept source-track paths.",
        "- Splits must group rows by source utterance and counterfactual family, not by target-task rows.",
        "",
        "## Adopted Tables",
        "",
        "- `results/tables/controlled_v2_manifest.csv`",
        "- `results/tables/controlled_v2_real_whisper_cer.csv`",
        "- `results/tables/audio_depth_v2_map_metadata.csv`",
        "- `results/tables/audiodepth_v2_metadata.csv`",
        "- `results/tables/controlled_v2_route_gap_filtered.csv`",
        "",
        "## Counts",
        "",
        f"- dataset rows: {audit['dataset_rows']}",
        f"- target quality distribution: {audit['target_quality']}",
        f"- target families: {audit['families']}",
    ]
    write_markdown(FIGURE_DIR / "generative_audiodepth_repo_input_audit.md", lines)


def main() -> None:
    args = parse_args()
    rows, quality_rows, audit = build_rows(args.limit)
    write_dataset(DATASET_CSV, rows)
    write_csv(QUALITY_CSV, quality_rows)
    write_repo_audit(audit)
    print(f"Wrote {len(rows)} promptable target rows to {DATASET_CSV.relative_to(DATASET_CSV.parents[2])}")


if __name__ == "__main__":
    main()
