from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize01(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return np.zeros_like(arr, dtype=np.float32)
    lo = float(np.percentile(finite, 2))
    hi = float(np.percentile(finite, 98))
    if hi <= lo:
        lo = float(finite.min())
        hi = float(finite.max())
    if hi <= lo:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip((arr - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in {"", None}:  # type: ignore[comparison-overlap]
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


TABLE_DIR = PROJECT_ROOT / "results" / "tables"
FIGURE_DIR = PROJECT_ROOT / "results" / "figures"
MODEL_DIR = PROJECT_ROOT / "models"
TARGET_DIR = PROJECT_ROOT / "resources" / "generative_audiodepth_targets"

CONTROLLED_V2_MANIFEST = TABLE_DIR / "controlled_v2_manifest.csv"
CONTROLLED_V2_CER = TABLE_DIR / "controlled_v2_real_whisper_cer.csv"
CONTROLLED_V2_FILTERED = TABLE_DIR / "controlled_v2_route_gap_filtered.csv"
ANALYSIS_MAP_METADATA = TABLE_DIR / "audio_depth_v2_map_metadata.csv"
DEPLOYABLE_MAP_METADATA = TABLE_DIR / "audiodepth_v2_metadata.csv"
BALANCED_PREDICTIONS = TABLE_DIR / "audio_depth_balanced_predictions.csv"
BALANCED_COMPARISON = TABLE_DIR / "audio_depth_balanced_router_comparison.csv"
STAGE2_GUARD = TABLE_DIR / "stage2_review_guard_comparison.csv"
SAFETY_AUDIT = TABLE_DIR / "end_to_end_router_safety_audit.csv"

DATASET_CSV = TABLE_DIR / "generative_audiodepth_dataset.csv"
QUALITY_CSV = TABLE_DIR / "generative_audiodepth_target_quality.csv"
TRAIN_CSV = TABLE_DIR / "generative_audiodepth_train.csv"
VALIDATION_CSV = TABLE_DIR / "generative_audiodepth_validation.csv"
TEST_CSV = TABLE_DIR / "generative_audiodepth_test.csv"
UNSEEN_OVERLAP_CSV = TABLE_DIR / "generative_audiodepth_unseen_overlap_test.csv"
UNSEEN_DOMINANCE_CSV = TABLE_DIR / "generative_audiodepth_unseen_dominance_test.csv"

TASKS = ["OVERLAP_MAP", "DOMINANCE_MAP", "UNCERTAINTY_MAP", "ROUTE_REGRET", "REVIEW_RISK"]
ROUTES = ["mixed", "separated", "cleaned"]
ROUTE_COSTS = {"mixed": 1.0, "separated": 1.8, "cleaned": 2.0, "review": 5.0}
MAP_TASKS = {"OVERLAP_MAP", "DOMINANCE_MAP", "UNCERTAINTY_MAP"}
VECTOR_TASKS = {"ROUTE_REGRET", "REVIEW_RISK"}


def stable_bucket(text: str, modulo: int = 100) -> int:
    return int(hashlib.sha1(text.encode("utf-8")).hexdigest(), 16) % modulo


def read_rows(path: Path) -> list[dict[str, str]]:
    return read_csv(path) if path.exists() else []


def rows_by_sample(path: Path) -> dict[str, dict[str, str]]:
    return {row["sample_id"]: row for row in read_rows(path) if row.get("sample_id")}


def sample_feature_keys() -> list[str]:
    return [
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
    ]


def feature_vector(row: dict[str, Any]) -> np.ndarray:
    return np.asarray([safe_float(row.get(key), 0.0) for key in sample_feature_keys()], dtype=np.float32)


def route_regrets(row: dict[str, Any]) -> dict[str, float]:
    values = {route: safe_float(row.get(f"{route}_cer"), math.nan) for route in ROUTES}
    finite = [v for v in values.values() if math.isfinite(v)]
    best = min(finite) if finite else 0.0
    return {route: round(values[route] - best, 6) if math.isfinite(values[route]) else 0.0 for route in ROUTES}


def oracle_route(row: dict[str, Any]) -> str:
    if row.get("oracle_route") in ROUTES:
        return str(row["oracle_route"])
    values = {route: safe_float(row.get(f"{route}_cer"), 999.0) for route in ROUTES}
    return min(values, key=values.get)


def min_route_cer(row: dict[str, Any]) -> float:
    return min(safe_float(row.get(f"{route}_cer"), 999.0) for route in ROUTES)


def review_needed(row: dict[str, Any], gap_threshold: float = 0.02, high_error_threshold: float = 0.6) -> bool:
    family = str(row.get("intended_family", ""))
    expected = str(row.get("expected_winner", ""))
    if "review" in family or expected == "review_needed":
        return True
    if safe_float(row.get("route_gap"), 1.0) <= gap_threshold:
        return True
    if min_route_cer(row) >= high_error_threshold:
        return True
    return False


def load_npy(path_text: str) -> np.ndarray:
    path = PROJECT_ROOT / path_text
    return np.load(path).astype(np.float32)


def save_target_array(sample_id: str, task: str, arr: np.ndarray) -> str:
    path = TARGET_DIR / task.lower() / f"{sample_id}.npy"
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, np.asarray(arr, dtype=np.float32))
    return rel(path)


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def mean_map(rows: Iterable[dict[str, str]], task: str) -> np.ndarray:
    arrays = [load_npy(row["target_path"]) for row in rows if row.get("target_task") == task and row.get("target_path")]
    if not arrays:
        return np.zeros((64, 96), dtype=np.float32)
    return np.mean(np.stack(arrays), axis=0).astype(np.float32)


def nearest_index(train_x: np.ndarray, query: np.ndarray) -> int:
    if train_x.size == 0:
        return 0
    distances = np.sum((train_x - query[None, :]) ** 2, axis=1)
    return int(np.argmin(distances))


def rankdata(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        rank = (i + j) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = rank
        i = j + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or len(xs) != len(ys):
        return 0.0
    rx = np.asarray(rankdata(xs), dtype=np.float64)
    ry = np.asarray(rankdata(ys), dtype=np.float64)
    if np.std(rx) == 0 or np.std(ry) == 0:
        return 0.0
    return round(float(np.corrcoef(rx, ry)[0, 1]), 6)


def write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def dataset_fieldnames() -> list[str]:
    return [
        "sample_id",
        "dataset_source",
        "split_hint",
        "mixed_wav_path",
        "source_track_1_path",
        "source_track_2_path",
        "deployable_map_path",
        "analysis_teacher_map_path",
        "reference_type",
        "overlap_ratio",
        "dominance_type",
        "target_family",
        "oracle_route",
        "route_gap",
        "mixed_cer",
        "separated_cer",
        "cleaned_cer",
        "mixed_regret",
        "separated_regret",
        "cleaned_regret",
        "review_needed",
        "source_utterance_ids",
        "counterfactual_family_id",
        "target_task",
        "target_path",
        "target_quality",
        "target_scope",
        "student_input_policy",
        *sample_feature_keys(),
    ]


def write_dataset(path: Path, rows: list[dict[str, Any]]) -> None:
    write_csv(path, rows, dataset_fieldnames())


def unique_samples(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for row in rows:
        sid = row["sample_id"]
        if sid in seen:
            continue
        seen.add(sid)
        out.append(row)
    return out
