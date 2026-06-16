from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .audio_depth_router_common import PROJECT_ROOT, read_csv, rel, write_csv
from .audio_depth_systematic_common import safe_float, stable_bucket, write_wav_mono
from .controlled_benchmark_common import draw_bar, draw_line
from .text_normalization import cer, normalize_asr_text


TABLE_DIR = PROJECT_ROOT / "results" / "tables"
FIGURE_DIR = PROJECT_ROOT / "results" / "figures"
MODEL_DIR = PROJECT_ROOT / "models"
V2_ROOT = PROJECT_ROOT / "resources" / "controlled_route_sensitive_v2"
V2_AUDIO = V2_ROOT / "audio"
V2_REFS = V2_ROOT / "references"
V2_MANIFEST = TABLE_DIR / "controlled_v2_manifest.csv"
V2_POOL = TABLE_DIR / "controlled_v2_candidate_pool.csv"
V2_TX = TABLE_DIR / "controlled_v2_real_whisper_transcripts.csv"
V2_CER = TABLE_DIR / "controlled_v2_real_whisper_cer.csv"
V2_RUNTIME = TABLE_DIR / "controlled_v2_real_whisper_runtime.csv"
V2_FILTERED = TABLE_DIR / "controlled_v2_route_gap_filtered.csv"
V2_DISTRIBUTION = TABLE_DIR / "controlled_v2_oracle_route_distribution.csv"
AUDIO_DEPTH_V2_MAP_DIR = PROJECT_ROOT / "resources" / "audio_depth_v2_maps"
AUDIO_DEPTH_V2_MAP_METADATA = TABLE_DIR / "audio_depth_v2_map_metadata.csv"
BALANCED_PREDICTIONS = TABLE_DIR / "audio_depth_balanced_predictions.csv"
BALANCED_COMPARISON = TABLE_DIR / "audio_depth_balanced_router_comparison.csv"
BALANCED_STATUS = TABLE_DIR / "audio_depth_balanced_model_status.csv"
BALANCED_TRAINING_LOG = TABLE_DIR / "audio_depth_balanced_training_log.csv"
BALANCED_PER_FAMILY = TABLE_DIR / "audio_depth_balanced_per_family.csv"
BALANCED_PER_ORACLE_ROUTE = TABLE_DIR / "audio_depth_balanced_per_oracle_route.csv"
BALANCED_REVIEW_CANDIDATES = TABLE_DIR / "audio_depth_balanced_review_candidates.csv"
BALANCED_CASE_STUDIES = TABLE_DIR / "audio_depth_balanced_case_studies.csv"


ROUTES = ["mixed", "separated", "cleaned"]


def add_noise(audio: np.ndarray, level: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if level <= 0:
        return audio.astype(np.float32)
    noise = rng.normal(0.0, level, size=len(audio)).astype(np.float32)
    return np.clip(audio + noise, -0.95, 0.95).astype(np.float32)


def smear(audio: np.ndarray, amount: float) -> np.ndarray:
    if amount <= 0:
        return audio.astype(np.float32)
    taps = max(2, int(3 + amount * 8))
    kernel = np.exp(-np.linspace(0, 2.5, taps)).astype(np.float32)
    kernel /= kernel.sum()
    return np.convolve(audio, kernel, mode="same").astype(np.float32)


def duplicate_tail(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    tail = audio[-min(len(audio), int(0.55 * sample_rate)) :]
    return np.concatenate([audio, np.zeros(int(0.08 * sample_rate), dtype=np.float32), tail]).astype(np.float32)


def route_metrics(reference: str, mixed: str, separated: str, cleaned: str) -> dict[str, Any]:
    vals = {
        "mixed_cer": cer(reference, mixed),
        "separated_cer": cer(reference, separated),
        "cleaned_cer": cer(reference, cleaned),
    }
    route_values = {"mixed": vals["mixed_cer"], "separated": vals["separated_cer"], "cleaned": vals["cleaned_cer"]}
    oracle = min(route_values, key=route_values.get)
    sorted_vals = sorted(float(v) for v in route_values.values())
    return {
        **vals,
        "oracle_route": oracle,
        "oracle_cer": route_values[oracle],
        "route_gap": round(sorted_vals[1] - sorted_vals[0], 6),
        "all_route_mean_cer": round(sum(sorted_vals) / 3, 6),
    }


def clean_text(text: str) -> str:
    norm = normalize_asr_text(text)
    # Remove adjacent duplicated halves/thirds caused by repeated source tracks.
    for parts in [2, 3]:
        if len(norm) > 8 and len(norm) % parts == 0:
            unit = len(norm) // parts
            chunk = norm[:unit]
            if chunk * parts == norm:
                return chunk
            chunks = [norm[i * unit : (i + 1) * unit] for i in range(parts)]
            if all(cer(chunk, other) <= 0.25 for other in chunks[1:]):
                return chunk
    half = len(norm) // 2
    if half > 5 and norm[:half] == norm[half : half * 2]:
        return norm[:half]
    if half > 8 and cer(norm[:half], norm[half : half * 2]) <= 0.25:
        return norm[:half]
    return norm


def mean(values: list[float]) -> float:
    return round(float(np.mean(values)), 6) if values else 0.0


def route_cer(row: dict[str, Any], route: str) -> float:
    return safe_float(row[f"{route}_cer"])


def route_winner_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {route: 0 for route in ROUTES}
    for row in rows:
        route = str(row.get("oracle_route", ""))
        if route in counts:
            counts[route] += 1
    return counts


def duplicate_density(text: str) -> float:
    norm = normalize_asr_text(text)
    if len(norm) < 12:
        return 0.0
    grams = [norm[i : i + 4] for i in range(0, len(norm) - 3)]
    if not grams:
        return 0.0
    return round(1.0 - (len(set(grams)) / len(grams)), 6)


def split_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    train, test = [], []
    for row in rows:
        (train if stable_bucket(row["sample_id"], 100) < 70 else test).append(row)
    return train, test
