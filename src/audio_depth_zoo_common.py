from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .audio_depth_map import generate_one
from .audio_depth_router_common import (
    CER_COLUMNS,
    LABEL_TO_METHOD,
    METHOD_TO_LABEL,
    PROJECT_ROOT,
    ROUTE_LABELS,
    analysis_channels,
    best_route_from_cers,
    deployable_channels,
    frame_energy,
    normalize01,
    pseudo_log_mel,
    read_csv,
    read_wav_mono,
    rel,
    route_cer,
    stft_magnitude,
    write_csv,
    write_json,
)
from .build_audio_depth_router_dataset import build_dataset


ZOO_DIR = PROJECT_ROOT / "models" / "audio_depth_zoo"
FEATURES_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_zoo_hybrid_features.csv"
TRAINING_LOG_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_zoo_training_log.csv"
MODEL_STATUS_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_zoo_model_status.csv"
PREDICTIONS_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_zoo_predictions.csv"
PERFORMANCE_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_zoo_performance.csv"
PER_CLASS_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_zoo_per_class_metrics.csv"
PER_TIER_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_zoo_per_tier_metrics.csv"
COMPARE_TO_ROUTER_V2_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_zoo_comparison_to_router_v2.csv"
CONFIDENCE_CASCADE_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_zoo_confidence_cascade.csv"
SUMMARY_MD = PROJECT_ROOT / "results" / "figures" / "audio_depth_zoo_summary.md"

MODEL_NAMES = [
    "mlp_handcrafted",
    "cnn_logmel",
    "cnn_depth",
    "cnn_depth_balanced",
    "resnet_tiny_depth",
    "crnn_depth",
    "patch_transformer_depth",
    "hybrid_late_fusion",
    "analysis_upper_bound_cnn",
]

DEPLOYABLE_MODES = {"deployable", "logmel"}
ALL_MODES = {"deployable", "logmel", "analysis"}


def safe_float(value: Any, default: float = math.nan) -> float:
    try:
        if value in {"", None, "NA", "na", "nan", "NaN"}:
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in {"", None, "NA", "na", "nan", "NaN"}:
            return default
        return int(float(value))
    except Exception:
        return default


def bool_score(value: Any, default: float = math.nan) -> float:
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return 1.0
    if text in {"false", "0", "no", "n"}:
        return 0.0
    return default


def ensure_rows() -> list[dict[str, Any]]:
    rows = build_dataset("deployable")
    return [dict(row) for row in rows if row.get("split") in {"dev", "test"}]


def sample_map_path(sample_id: str, mode: str) -> Path:
    return PROJECT_ROOT / f"resources/audio_depth_maps/{mode}/{sample_id}.npy"


def ensure_maps(mode: str, rows: list[dict[str, Any]] | None = None, overwrite: bool = False) -> list[dict[str, Any]]:
    rows = rows or ensure_rows()
    generated: list[dict[str, Any]] = []
    for row in rows:
        path = sample_map_path(str(row["sample_id"]), mode)
        if path.exists() and not overwrite:
            continue
        result = generate_one(row, mode, preview=False, overwrite=overwrite)
        generated.append(result)
    return generated


def map_channels_for_mode(mode: str) -> int:
    return {"logmel": 1, "deployable": 3, "analysis": 3}.get(mode, 3)


def load_map(sample_id: str, mode: str) -> np.ndarray | None:
    path = sample_map_path(sample_id, mode)
    if not path.exists():
        return None
    return np.load(path).astype(np.float32)


def route_label_to_index(label: str) -> int:
    return ROUTE_LABELS.index(label)


def row_to_cer_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "mixed_cer": safe_float(row.get("mixed_cer")),
        "separated_cer": safe_float(row.get("separated_cer")),
        "cleaned_cer": safe_float(row.get("cleaned_cer")),
        "best_route_label": row.get("best_route_label") or best_route_from_cers(row),
    }


def _resample_1d(values: np.ndarray, length: int) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32).reshape(-1)
    if values.size == 0:
        return np.zeros(length, dtype=np.float32)
    if values.size == length:
        return values.astype(np.float32)
    if length <= 1:
        return np.asarray([float(values.mean())], dtype=np.float32)
    old_x = np.linspace(0.0, 1.0, num=values.size, dtype=np.float32)
    new_x = np.linspace(0.0, 1.0, num=length, dtype=np.float32)
    return np.interp(new_x, old_x, values).astype(np.float32)


def spectral_flux_stats(audio: np.ndarray) -> tuple[float, float]:
    mag = stft_magnitude(audio)
    norm = normalize01(np.log1p(mag))
    flux = np.diff(norm, axis=1, prepend=norm[:, :1])
    flux = np.maximum(flux, 0.0)
    return float(np.mean(flux)), float(np.std(flux))


def handcrafted_audio_features(row: dict[str, Any]) -> dict[str, float]:
    audio_path = PROJECT_ROOT / str(row["audio_path"])
    audio, sr = read_wav_mono(audio_path)
    duration = len(audio) / float(sr) if sr else 0.0
    energy = frame_energy(audio)
    energy_norm = normalize01(energy)
    spec_mean, spec_std = spectral_flux_stats(audio)
    deployable_map = load_map(str(row["sample_id"]), "deployable")
    if deployable_map is None:
        deployable_map = deployable_channels(audio, sr)
    overlap_proxy = deployable_map[1]
    uncertainty_proxy = deployable_map[2]
    return {
        "duration": float(duration),
        "mean_energy": float(np.mean(energy)) if energy.size else 0.0,
        "max_energy": float(np.max(energy)) if energy.size else 0.0,
        "spectral_flux_mean": spec_mean,
        "spectral_flux_std": spec_std,
        "overlap_proxy_mean": float(np.mean(overlap_proxy)),
        "overlap_proxy_max": float(np.max(overlap_proxy)),
        "uncertainty_proxy_mean": float(np.mean(uncertainty_proxy)),
        "uncertainty_proxy_max": float(np.max(uncertainty_proxy)),
        "energy_norm_mean": float(np.mean(energy_norm)) if energy_norm.size else 0.0,
    }


def transcript_risk_features(sample_id: str) -> dict[str, Any]:
    routing_path = PROJECT_ROOT / "results" / "tables" / "synthetic_split_routing_decisions.csv"
    features = {
        "mixed_segment_count": math.nan,
        "separated_segment_count": math.nan,
        "cleaned_removed_count": math.nan,
        "length_ratio": math.nan,
        "repetition_score": math.nan,
        "method_disagreement_score": math.nan,
        "separated_length": math.nan,
        "mixed_length": math.nan,
        "cleaned_length": math.nan,
        "selected_method_v2": "",
        "decision_rule_v2": "",
    }
    if routing_path.exists():
        rows = [row for row in read_csv(routing_path) if row.get("sample_id") == sample_id and row.get("strategy") == "v2_full_features"]
        if rows:
            row = rows[0]
            mixed_segments = safe_float(row.get("mixed_segments_count"))
            separated_segments = safe_float(row.get("separated_segments_count"))
            cleaned_segments = safe_float(row.get("cleaned_segments_count"))
            mixed_length = safe_float(row.get("mixed_text_length"))
            separated_length = safe_float(row.get("separated_text_length"))
            cleaned_length = safe_float(row.get("cleaned_text_length"))
            features.update(
                {
                    "mixed_segment_count": mixed_segments,
                    "separated_segment_count": separated_segments,
                    "cleaned_removed_count": safe_float(row.get("duplicate_removed_count")),
                    "length_ratio": safe_float(row.get("text_length_ratio")),
                    "repetition_score": max(0.0, separated_length - mixed_length) / max(mixed_length, 1.0),
                    "method_disagreement_score": abs(separated_length - mixed_length) + abs(cleaned_length - mixed_length),
                    "separated_length": separated_length,
                    "mixed_length": mixed_length,
                    "cleaned_length": cleaned_length,
                    "selected_method_v2": row.get("selected_method", ""),
                    "decision_rule_v2": row.get("decision_rule", ""),
                }
            )
    v2_path = PROJECT_ROOT / "results" / "tables" / "routing_decisions_v2.csv"
    if v2_path.exists():
        rows = [row for row in read_csv(v2_path) if row.get("case_id", "").lower() == sample_id.lower()]
        if rows:
            row = rows[0]
            features.update(
                {
                    "selected_method_v2": row.get("selected_method", features["selected_method_v2"]),
                    "decision_rule_v2": row.get("decision_rule", features["decision_rule_v2"]),
                    "mixed_segment_count": safe_float(row.get("mixed_segments_count"), features["mixed_segment_count"]),
                    "separated_segment_count": safe_float(row.get("separated_segments_count"), features["separated_segment_count"]),
                    "cleaned_removed_count": safe_float(row.get("duplicate_removed_count"), features["cleaned_removed_count"]),
                    "length_ratio": safe_float(row.get("text_length_ratio"), features["length_ratio"]),
                    "repetition_score": bool_score(row.get("separated_unstable"), features["repetition_score"]),
                    "method_disagreement_score": bool_score(row.get("cleaned_closer_to_mixed"), features["method_disagreement_score"]),
                    "separated_length": safe_float(row.get("separated_text_length"), features["separated_length"]),
                    "mixed_length": safe_float(row.get("mixed_text_length"), features["mixed_length"]),
                    "cleaned_length": safe_float(row.get("cleaned_text_length"), features["cleaned_length"]),
                }
            )
    return features


def build_hybrid_features_table() -> list[dict[str, Any]]:
    rows = ensure_rows()
    output: list[dict[str, Any]] = []
    for row in rows:
        audio_features = handcrafted_audio_features(row)
        transcript_features = transcript_risk_features(str(row["sample_id"]))
        deployable_path = sample_map_path(str(row["sample_id"]), "deployable")
        logmel_path = sample_map_path(str(row["sample_id"]), "logmel")
        analysis_path = sample_map_path(str(row["sample_id"]), "analysis")
        entry = {
            "sample_id": row["sample_id"],
            "split": row.get("split", ""),
            "overlap_tier": row.get("overlap_tier", row.get("tier", "")),
            "best_route_label": row.get("best_route_label", best_route_from_cers(row)),
            "mixed_cer": safe_float(row.get("mixed_cer")),
            "separated_cer": safe_float(row.get("separated_cer")),
            "cleaned_cer": safe_float(row.get("cleaned_cer")),
            "map_path_deployable": rel(deployable_path),
            "map_path_logmel": rel(logmel_path),
            "map_path_analysis": rel(analysis_path) if analysis_path.exists() else "",
            **audio_features,
            **transcript_features,
        }
        output.append(entry)
    fieldnames = [
        "sample_id",
        "split",
        "overlap_tier",
        "best_route_label",
        "mixed_cer",
        "separated_cer",
        "cleaned_cer",
        "map_path_deployable",
        "map_path_logmel",
        "map_path_analysis",
        "duration",
        "mean_energy",
        "max_energy",
        "spectral_flux_mean",
        "spectral_flux_std",
        "overlap_proxy_mean",
        "overlap_proxy_max",
        "uncertainty_proxy_mean",
        "uncertainty_proxy_max",
        "energy_norm_mean",
        "mixed_segment_count",
        "separated_segment_count",
        "cleaned_removed_count",
        "length_ratio",
        "repetition_score",
        "method_disagreement_score",
        "separated_length",
        "mixed_length",
        "cleaned_length",
        "selected_method_v2",
        "decision_rule_v2",
    ]
    write_csv(FEATURES_CSV, output, fieldnames)
    return output


def load_hybrid_features() -> list[dict[str, Any]]:
    if FEATURES_CSV.exists():
        return read_csv(FEATURES_CSV)
    return build_hybrid_features_table()


def parse_float_list(row: dict[str, Any], keys: Iterable[str]) -> list[float]:
    return [safe_float(row.get(key)) for key in keys]


def route_from_prediction_index(index: int) -> str:
    return ROUTE_LABELS[index % len(ROUTE_LABELS)]


def majority_label(rows: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.get("best_route_label", "")] = counts.get(row.get("best_route_label", ""), 0) + 1
    return max(counts, key=counts.get) if counts else ROUTE_LABELS[0]


def feature_keys() -> list[str]:
    return [
        "duration",
        "mean_energy",
        "max_energy",
        "spectral_flux_mean",
        "spectral_flux_std",
        "overlap_proxy_mean",
        "overlap_proxy_max",
        "uncertainty_proxy_mean",
        "uncertainty_proxy_max",
        "energy_norm_mean",
        "mixed_segment_count",
        "separated_segment_count",
        "cleaned_removed_count",
        "length_ratio",
        "repetition_score",
        "method_disagreement_score",
        "separated_length",
        "mixed_length",
        "cleaned_length",
    ]


def best_route_for_row(row: dict[str, Any]) -> str:
    return row.get("best_route_label") or best_route_from_cers(row)


def available_modes_for_row(row: dict[str, Any]) -> list[str]:
    modes = ["deployable", "logmel"]
    if PROJECT_ROOT.joinpath(f"resources/audio_depth_maps/analysis/{row['sample_id']}.npy").exists():
        modes.append("analysis")
    return modes


def table_from_rows(rows: list[dict[str, Any]], fieldnames: list[str]) -> list[dict[str, Any]]:
    return [{key: row.get(key, "") for key in fieldnames} for row in rows]
