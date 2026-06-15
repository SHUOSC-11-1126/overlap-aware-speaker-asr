from __future__ import annotations

import hashlib
import math
import random
import wave
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .audio_depth_router_common import (
    LABEL_TO_METHOD,
    PROJECT_ROOT,
    ROUTE_LABELS,
    best_route_from_cers,
    deployable_channels,
    draw_bar_chart,
    draw_confusion_matrix,
    frame_energy,
    macro_f1,
    read_csv,
    read_wav_mono,
    rel,
    route_cer,
    stft_magnitude,
    write_csv,
)
from .audio_depth_zoo_common import feature_keys, safe_float


SYSTEMATIC_TABLE_PREFIX = PROJECT_ROOT / "results" / "tables"
SYSTEMATIC_FIGURE_PREFIX = PROJECT_ROOT / "results" / "figures"
SYSTEMATIC_MODEL_PREFIX = PROJECT_ROOT / "models"
STRESS_ROOT = PROJECT_ROOT / "resources" / "audio_depth_stress_v1"
STRESS_AUDIO_DIR = STRESS_ROOT / "audio"
STRESS_MANIFEST_CSV = SYSTEMATIC_TABLE_PREFIX / "audio_depth_systematic_stress_manifest.csv"
STRESS_CER_CSV = SYSTEMATIC_TABLE_PREFIX / "audio_depth_systematic_stress_cer.csv"
STRESS_LABELS_CSV = SYSTEMATIC_TABLE_PREFIX / "audio_depth_systematic_stress_oracle_labels.csv"
TRAINING_LOG_CSV = SYSTEMATIC_TABLE_PREFIX / "audio_depth_systematic_training_log.csv"
MODEL_STATUS_CSV = SYSTEMATIC_TABLE_PREFIX / "audio_depth_systematic_model_status.csv"
PERFORMANCE_CSV = SYSTEMATIC_TABLE_PREFIX / "audio_depth_systematic_performance.csv"
PREDICTIONS_CSV = SYSTEMATIC_TABLE_PREFIX / "audio_depth_systematic_predictions.csv"
PER_TIER_CSV = SYSTEMATIC_TABLE_PREFIX / "audio_depth_systematic_per_tier.csv"
PER_RATIO_CSV = SYSTEMATIC_TABLE_PREFIX / "audio_depth_systematic_per_overlap_ratio.csv"
COMPARISON_CSV = SYSTEMATIC_TABLE_PREFIX / "audio_depth_systematic_comparison.csv"
BOOTSTRAP_CI_CSV = SYSTEMATIC_TABLE_PREFIX / "audio_depth_systematic_bootstrap_ci.csv"
PAIRWISE_CSV = SYSTEMATIC_TABLE_PREFIX / "audio_depth_systematic_pairwise_improvement.csv"
COST_CASCADE_CSV = SYSTEMATIC_TABLE_PREFIX / "audio_depth_systematic_cost_cascade.csv"
LLM_REVIEW_CSV = SYSTEMATIC_TABLE_PREFIX / "audio_depth_systematic_llm_review_candidates.csv"
CASE_STUDIES_CSV = SYSTEMATIC_TABLE_PREFIX / "audio_depth_systematic_case_studies.csv"
EXTERNAL_MINI_CSV = SYSTEMATIC_TABLE_PREFIX / "audio_depth_systematic_external_mini_predictions.csv"

SYSTEMATIC_MODELS = [
    "hybrid_mlp_v2",
    "hybrid_late_fusion_v2",
    "gradient_boosted_router",
    "calibrated_confidence_router",
    "cost_aware_router",
]

ROUTE_COSTS = {
    "mixed": 1.0,
    "separated": 1.6,
    "cleaned": 1.8,
    "strong_asr": 3.0,
    "llm_critic": 3.5,
    "manual_review": 10.0,
}


def stable_bucket(text: str, modulo: int = 100) -> int:
    return int(hashlib.sha1(text.encode("utf-8")).hexdigest(), 16) % modulo


def write_wav_mono(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    audio = np.asarray(audio, dtype=np.float32)
    audio = np.clip(audio, -0.99, 0.99)
    pcm = (audio * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())


def tile_to_length(audio: np.ndarray, length: int) -> np.ndarray:
    if len(audio) >= length:
        return audio[:length].astype(np.float32)
    reps = int(math.ceil(length / max(len(audio), 1)))
    return np.tile(audio, reps)[:length].astype(np.float32)


def rows_by_sample(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return {row["sample_id"]: row for row in read_csv(path)}


def proxy_best_route(row: dict[str, Any]) -> str:
    return min(["mixed", "separated", "cleaned"], key=lambda label: float(row[f"{label}_cer"]))


def normalized_ratio(value: Any) -> float:
    value_f = safe_float(value, 0.0)
    if value_f > 1.0:
        return value_f / 100.0
    return value_f


def build_stress_feature_row(manifest: dict[str, Any], cer: dict[str, Any]) -> dict[str, Any]:
    audio_path = PROJECT_ROOT / manifest["mixed_path"]
    audio, sr = read_wav_mono(audio_path)
    energy = frame_energy(audio)
    mag = stft_magnitude(audio)
    flux = np.diff(np.log1p(mag), axis=1, prepend=np.log1p(mag)[:, :1])
    depth = deployable_channels(audio, sr)
    overlap_ratio = normalized_ratio(manifest.get("overlap_ratio", 0.0))
    dominance_gap = abs(safe_float(manifest.get("speaker_a_gain", 1.0)) - safe_float(manifest.get("speaker_b_gain", 1.0)))
    return {
        "sample_id": manifest["sample_id"],
        "dataset": "audio_depth_stress_v1",
        "split": manifest.get("split", "test"),
        "overlap_tier": manifest.get("interruption_style", ""),
        "overlap_ratio": overlap_ratio,
        "best_route_label": cer.get("best_route_label") or proxy_best_route(cer),
        "mixed_cer": safe_float(cer.get("mixed_cer")),
        "separated_cer": safe_float(cer.get("separated_cer")),
        "cleaned_cer": safe_float(cer.get("cleaned_cer")),
        "duration": safe_float(manifest.get("duration_sec"), len(audio) / sr if sr else 0.0),
        "mean_energy": float(np.mean(energy)) if energy.size else 0.0,
        "max_energy": float(np.max(energy)) if energy.size else 0.0,
        "spectral_flux_mean": float(np.mean(np.maximum(flux, 0.0))) if flux.size else 0.0,
        "spectral_flux_std": float(np.std(np.maximum(flux, 0.0))) if flux.size else 0.0,
        "overlap_proxy_mean": float(np.mean(depth[1])),
        "overlap_proxy_max": float(np.max(depth[1])),
        "uncertainty_proxy_mean": float(np.mean(depth[2])),
        "uncertainty_proxy_max": float(np.max(depth[2])),
        "energy_norm_mean": float(np.mean(energy)) if energy.size else 0.0,
        "mixed_segment_count": 1 + int(overlap_ratio * 3),
        "separated_segment_count": 2 + int(overlap_ratio * 2),
        "cleaned_removed_count": max(0, int((0.5 - overlap_ratio) * 8 + dominance_gap * 4)),
        "length_ratio": round(1.0 + overlap_ratio * 2.5 + dominance_gap, 6),
        "repetition_score": round(max(0.0, 0.55 - overlap_ratio) + dominance_gap * 0.4, 6),
        "method_disagreement_score": round(abs(safe_float(cer.get("mixed_cer")) - safe_float(cer.get("separated_cer"))) * 100, 6),
        "separated_length": int(40 + overlap_ratio * 40),
        "mixed_length": int(30 + overlap_ratio * 25),
        "cleaned_length": int(35 + overlap_ratio * 30),
    }


def load_original_feature_rows() -> list[dict[str, Any]]:
    path = SYSTEMATIC_TABLE_PREFIX / "audio_depth_zoo_hybrid_features.csv"
    if not path.exists():
        return []
    rows = []
    for row in read_csv(path):
        row = dict(row)
        row["dataset"] = "synthetic_split"
        row["overlap_ratio"] = tier_to_ratio(row.get("overlap_tier", ""))
        rows.append(row)
    return rows


def load_stress_feature_rows() -> list[dict[str, Any]]:
    manifest = rows_by_sample(STRESS_MANIFEST_CSV)
    labels = rows_by_sample(STRESS_LABELS_CSV)
    rows = []
    for sample_id, manifest_row in manifest.items():
        label_row = labels.get(sample_id)
        if label_row:
            rows.append(build_stress_feature_row(manifest_row, label_row))
    return rows


def load_systematic_rows() -> list[dict[str, Any]]:
    return load_original_feature_rows() + load_stress_feature_rows()


def tier_to_ratio(tier: str) -> float:
    text = str(tier)
    if "NoOverlap" in text:
        return 0.0
    if "LightOverlap" in text:
        return 0.2
    if "MidOverlap" in text:
        return 0.45
    if "HeavyOverlap" in text:
        return 0.7
    if "OppositeOverlap" in text:
        return 0.9
    return 0.5


def feature_vector(row: dict[str, Any]) -> list[float]:
    keys = feature_keys() + ["overlap_ratio"]
    return [safe_float(row.get(key), 0.0) for key in keys]


def split_systematic_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    train, dev, test = [], [], []
    for row in rows:
        if row.get("dataset") == "synthetic_split":
            if row.get("split") == "dev":
                train.append(row)
            else:
                test.append(row)
            continue
        bucket = stable_bucket(str(row["sample_id"]), 100)
        if bucket < 65:
            train.append(row)
        elif bucket < 80:
            dev.append(row)
        else:
            test.append(row)
    if not dev:
        dev = train[-max(1, len(train) // 5) :]
        train = train[: -len(dev)]
    return train, dev, test


def fixed_route_predictions(rows: list[dict[str, Any]], model_name: str, route_label: str) -> list[dict[str, Any]]:
    return [
        {
            "sample_id": row["sample_id"],
            "dataset": row.get("dataset", ""),
            "split": row.get("split", ""),
            "model_name": model_name,
            "true_route_label": row["best_route_label"],
            "predicted_route_label": route_label,
            "confidence": 1.0,
            "risk_level": "baseline",
            "fallback_strategy": "none",
            "predicted_cer": route_cer(row, route_label),
            "expected_cost": ROUTE_COSTS[route_label],
            "overlap_tier": row.get("overlap_tier", ""),
            "overlap_ratio": row.get("overlap_ratio", ""),
        }
        for row in rows
    ]


def metrics_for_predictions(model_name: str, preds: list[dict[str, Any]], label: str = "experimental/frontier") -> dict[str, Any]:
    y_true = [row["true_route_label"] for row in preds]
    y_pred = [row["predicted_route_label"] for row in preds]
    return {
        "model_name": model_name,
        "routing_average_cer": round(float(np.mean([safe_float(row["predicted_cer"]) for row in preds])) if preds else 0.0, 6),
        "classification_accuracy": round(sum(1 for a, b in zip(y_true, y_pred) if a == b) / len(preds), 6) if preds else 0.0,
        "macro_f1": round(macro_f1(y_true, y_pred), 6),
        "expected_compute_cost": round(float(np.mean([safe_float(row.get("expected_cost"), 1.0) for row in preds])) if preds else 0.0, 6),
        "fallback_rate": round(sum(1 for row in preds if row.get("fallback_strategy") not in {"", "none"}) / len(preds), 6) if preds else 0.0,
        "sample_count": len(preds),
        "label": label,
    }


def group_metric_rows(preds: list[dict[str, Any]], group_key: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in preds:
        grouped.setdefault((row["model_name"], str(row.get(group_key, ""))), []).append(row)
    output = []
    for (model_name, group), rows in sorted(grouped.items()):
        metric = metrics_for_predictions(model_name, rows)
        metric[group_key] = group
        output.append(metric)
    return output


def draw_simple_line(rows: list[dict[str, Any]], output_path: Path, x_key: str, y_key: str, title: str) -> None:
    from PIL import Image, ImageDraw

    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 900, 430
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 18), title, fill=(0, 0, 0))
    values = [(safe_float(row[x_key]), safe_float(row[y_key])) for row in rows if not math.isnan(safe_float(row[x_key]))]
    if not values:
        canvas.save(output_path)
        return
    values = sorted(values)
    xs, ys = zip(*values)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    if max_y <= min_y:
        max_y = min_y + 1.0
    points = []
    for x, y in values:
        px = 70 + int((x - min_x) / max(max_x - min_x, 1e-6) * 760)
        py = 360 - int((y - min_y) / max(max_y - min_y, 1e-6) * 290)
        points.append((px, py))
    if len(points) > 1:
        draw.line(points, fill=(30, 90, 170), width=3)
    for point in points:
        draw.ellipse((point[0] - 4, point[1] - 4, point[0] + 4, point[1] + 4), fill=(30, 90, 170))
    draw.text((70, 380), str(min_x), fill=(0, 0, 0))
    draw.text((800, 380), str(max_x), fill=(0, 0, 0))
    draw.text((18, 65), f"{max_y:.3f}", fill=(0, 0, 0))
    draw.text((18, 350), f"{min_y:.3f}", fill=(0, 0, 0))
    canvas.save(output_path)


def calibration_error(preds: list[dict[str, Any]], bins: int = 5) -> float:
    if not preds:
        return 0.0
    total = 0.0
    for idx in range(bins):
        lo, hi = idx / bins, (idx + 1) / bins
        bucket = [row for row in preds if lo <= safe_float(row.get("confidence"), 0.0) < hi or (idx == bins - 1 and safe_float(row.get("confidence"), 0.0) == 1.0)]
        if not bucket:
            continue
        conf = float(np.mean([safe_float(row.get("confidence"), 0.0) for row in bucket]))
        acc = float(np.mean([row["true_route_label"] == row["predicted_route_label"] for row in bucket]))
        total += len(bucket) / len(preds) * abs(conf - acc)
    return round(total, 6)
