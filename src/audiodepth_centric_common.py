from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from .audio_depth_router_common import (
    PROJECT_ROOT,
    frame_energy,
    normalize01,
    read_csv,
    read_wav_mono,
    rel,
    resize_2d,
    stft_magnitude,
    write_csv,
)
from .audio_depth_systematic_common import safe_float, stable_bucket
from .balanced_v2_common import V2_CER, V2_MANIFEST
from .controlled_benchmark_common import CER_CSV as CONTROLLED_V1_CER
from .controlled_benchmark_common import MANIFEST_CSV as CONTROLLED_V1_MANIFEST


TABLE_DIR = PROJECT_ROOT / "results" / "tables"
FIGURE_DIR = PROJECT_ROOT / "results" / "figures"
MODEL_DIR = PROJECT_ROOT / "models"
MAP_DIR = PROJECT_ROOT / "resources" / "audiodepth_v2_maps"
METADATA_CSV = TABLE_DIR / "audiodepth_v2_metadata.csv"
FEATURE_SUMMARY_CSV = TABLE_DIR / "audiodepth_v2_feature_summary.csv"
FEATURE_CORR_CSV = TABLE_DIR / "audiodepth_v2_feature_route_correlation.csv"
PROBE_PERFORMANCE_CSV = TABLE_DIR / "audiodepth_centric_probe_performance.csv"
PROBE_EMBEDDINGS_CSV = TABLE_DIR / "audiodepth_centric_probe_embeddings.csv"
GATE_PREDICTIONS_CSV = TABLE_DIR / "audiodepth_gate_predictions.csv"
GATE_PERFORMANCE_CSV = TABLE_DIR / "audiodepth_gate_performance.csv"
GATE_PER_FAMILY_CSV = TABLE_DIR / "audiodepth_gate_per_family.csv"
CASCADE_CSV = TABLE_DIR / "audiodepth_two_stage_cascade.csv"
CASCADE_COST_CSV = TABLE_DIR / "audiodepth_two_stage_cost.csv"
ABLATION_CSV = TABLE_DIR / "audiodepth_feature_ablation.csv"

ROUTES = ["mixed", "separated", "cleaned"]
GATE_LABELS = ["easy_mixed", "likely_separation_helpful", "ambiguous_needs_text_probe", "review_risk"]


def entropy01(arr: np.ndarray, axis: int = 0) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    arr = np.maximum(arr, 1e-8)
    probs = arr / np.maximum(arr.sum(axis=axis, keepdims=True), 1e-8)
    ent = -np.sum(probs * np.log(probs + 1e-8), axis=axis, keepdims=True)
    max_ent = math.log(max(arr.shape[axis], 2))
    return (ent / max_ent).astype(np.float32)


def zcr_frames(audio: np.ndarray, n_fft: int = 512, hop: int = 160) -> np.ndarray:
    if len(audio) < n_fft:
        audio = np.pad(audio, (0, n_fft - len(audio)))
    frame_count = 1 + max(0, (len(audio) - n_fft) // hop)
    windows = np.lib.stride_tricks.sliding_window_view(audio, n_fft)[::hop][:frame_count]
    signs = np.signbit(windows)
    return np.mean(signs[:, 1:] != signs[:, :-1], axis=1).astype(np.float32)[None, :]


def deployable_audiodepth_v2(audio: np.ndarray, sample_rate: int, height: int = 128, width: int = 256) -> np.ndarray:
    del sample_rate
    mag = stft_magnitude(audio)
    log_mag = np.log1p(mag)
    logmel = resize_2d(log_mag, (height, width))
    norm_mag = normalize01(log_mag)
    energy = frame_energy(audio)[None, :]
    energy_n = normalize01(energy)
    energy_var = np.abs(np.diff(energy_n, axis=1, prepend=energy_n[:, :1]))
    flatness = np.exp(np.mean(np.log(np.maximum(mag, 1e-8)), axis=0, keepdims=True)) / np.maximum(np.mean(mag, axis=0, keepdims=True), 1e-8)
    spectral_entropy = entropy01(mag, axis=0)
    high_band_density = (norm_mag > 0.60).mean(axis=0, keepdims=True)
    zcr = zcr_frames(audio)
    overlap_proxy = resize_2d(0.35 * high_band_density + 0.20 * spectral_entropy + 0.20 * normalize01(flatness) + 0.15 * normalize01(zcr) + 0.10 * energy_var, (height, width))
    flux = np.mean(np.maximum(np.diff(norm_mag, axis=1, prepend=norm_mag[:, :1]), 0.0), axis=0, keepdims=True)
    band_conflict = np.std(norm_mag, axis=0, keepdims=True)
    nonstationarity = np.abs(np.diff(spectral_entropy, axis=1, prepend=spectral_entropy[:, :1]))
    uncertainty_proxy = resize_2d(0.35 * normalize01(flux) + 0.25 * normalize01(band_conflict) + 0.25 * nonstationarity + 0.15 * energy_var, (height, width))
    return np.stack([logmel, overlap_proxy, uncertainty_proxy]).astype(np.float32)


def map_stats(arr: np.ndarray) -> dict[str, float]:
    names = ["logmel", "overlap_proxy", "uncertainty_proxy"]
    out: dict[str, float] = {}
    for idx, name in enumerate(names):
        ch = arr[idx]
        out[f"{name}_mean"] = round(float(np.mean(ch)), 6)
        out[f"{name}_max"] = round(float(np.max(ch)), 6)
        out[f"{name}_std"] = round(float(np.std(ch)), 6)
        out[f"{name}_p90"] = round(float(np.percentile(ch, 90)), 6)
    out["overlap_uncertainty_product"] = round(float(np.mean(arr[1] * arr[2])), 6)
    return out


def save_preview(arr: np.ndarray, path: Path, title: str) -> None:
    labels = ["C1 logmel", "C2 overlap_proxy", "C3 uncertainty_proxy"]
    panel_w, panel_h = 300, 170
    canvas = Image.new("RGB", (panel_w * 3, panel_h + 42), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 8), title[:120], fill=(0, 0, 0))
    for idx, label in enumerate(labels):
        img = Image.fromarray(np.uint8(normalize01(arr[idx]) * 255), mode="L").convert("RGB")
        img = img.resize((panel_w, panel_h), Image.Resampling.BILINEAR)
        d = ImageDraw.Draw(img)
        d.rectangle((0, 0, panel_w, 22), fill=(0, 0, 0))
        d.text((8, 5), label, fill=(255, 255, 255))
        canvas.paste(img, (idx * panel_w, 42))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)


def source_rows(source: str) -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    if source == "controlled_v2" and V2_MANIFEST.exists():
        manifest = read_csv(V2_MANIFEST)
        labels = {row["sample_id"]: row for row in read_csv(V2_CER)} if V2_CER.exists() else {}
        return manifest, labels
    if source == "controlled_v1" and CONTROLLED_V1_MANIFEST.exists():
        manifest = read_csv(CONTROLLED_V1_MANIFEST)
        labels = {row["sample_id"]: row for row in read_csv(CONTROLLED_V1_CER)} if CONTROLLED_V1_CER.exists() else {}
        return manifest, labels
    return [], {}


def labelled_metadata() -> list[dict[str, str]]:
    rows = read_csv(METADATA_CSV) if METADATA_CSV.exists() else []
    return [row for row in rows if row.get("oracle_route") in ROUTES and row.get("route_gap", "") != ""]


def target_family(row: dict[str, str]) -> str:
    return row.get("intended_family") or row.get("style") or row.get("overlap_tier") or "unknown"


def min_route_cer(row: dict[str, str]) -> float:
    return min(safe_float(row.get("mixed_cer")), safe_float(row.get("separated_cer")), safe_float(row.get("cleaned_cer")))


def gate_label(row: dict[str, str], gap_threshold: float = 0.02, risk_threshold: float = 0.6) -> str:
    if min_route_cer(row) > risk_threshold:
        return "review_risk"
    if safe_float(row.get("route_gap")) < gap_threshold:
        return "ambiguous_needs_text_probe"
    if row.get("oracle_route") == "mixed":
        return "easy_mixed"
    if row.get("oracle_route") == "separated":
        return "likely_separation_helpful"
    return "ambiguous_needs_text_probe"


def feature_vector(row: dict[str, Any]) -> list[float]:
    keys = [
        "logmel_mean",
        "logmel_std",
        "overlap_proxy_mean",
        "overlap_proxy_max",
        "overlap_proxy_std",
        "overlap_proxy_p90",
        "uncertainty_proxy_mean",
        "uncertainty_proxy_max",
        "uncertainty_proxy_std",
        "uncertainty_proxy_p90",
        "overlap_uncertainty_product",
    ]
    return [safe_float(row.get(key)) for key in keys]


def split_train_test(rows: list[dict[str, str]], key: str = "sample_id") -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    train, test = [], []
    for row in rows:
        (train if stable_bucket(row[key], 100) < 70 else test).append(row)
    return train, test or rows


def macro_f1_labels(y_true: list[str], y_pred: list[str], labels: list[str]) -> float:
    scores = []
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        scores.append((2 * precision * recall / (precision + recall)) if precision + recall else 0.0)
    return round(float(np.mean(scores)), 6) if scores else 0.0


def accuracy(y_true: list[str], y_pred: list[str]) -> float:
    return round(float(np.mean([a == b for a, b in zip(y_true, y_pred)])), 6) if y_true else 0.0


def route_cer(row: dict[str, str], route: str) -> float:
    return safe_float(row.get(f"{route}_cer"))


def draw_bar(rows: list[dict[str, Any]], path: Path, label_key: str, value_key: str, title: str) -> None:
    width, height = 960, 460
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 18), title, fill=(0, 0, 0))
    vals = [safe_float(row.get(value_key)) for row in rows]
    min_val = min(vals + [0.0])
    max_val = max(vals + [1e-6])
    span = max(max_val - min_val, 1e-6)
    zero_y = 360 - int(260 * (0.0 - min_val) / span)
    bar_w = max(24, int(820 / max(len(rows), 1)))
    for idx, row in enumerate(rows):
        value = safe_float(row.get(value_key))
        x0 = 80 + idx * bar_w
        y_value = 360 - int(260 * (value - min_val) / span)
        y0, y1 = sorted([zero_y, y_value])
        draw.rectangle((x0, y0, x0 + bar_w - 7, y1), fill=(58, 116, 165))
        draw.text((x0, max(42, y0 - 16)), f"{value:.3f}", fill=(0, 0, 0))
        draw.text((x0, 370), str(row.get(label_key, ""))[:14], fill=(0, 0, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)


def draw_confusion(y_true: list[str], y_pred: list[str], labels: list[str], path: Path, title: str) -> None:
    cell = 96
    margin = 190
    canvas = Image.new("RGB", (margin + cell * len(labels) + 20, margin + cell * len(labels) + 40), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 18), title, fill=(0, 0, 0))
    matrix = [[sum(1 for t, p in zip(y_true, y_pred) if t == a and p == b) for b in labels] for a in labels]
    max_value = max([v for row in matrix for v in row] + [1])
    for i, a in enumerate(labels):
        draw.text((20, margin + i * cell + 34), a[:24], fill=(0, 0, 0))
        draw.text((margin + i * cell + 8, 112), labels[i][:12], fill=(0, 0, 0))
        for j, value in enumerate(matrix[i]):
            shade = 255 - int(170 * value / max_value)
            x0, y0 = margin + j * cell, margin + i * cell
            draw.rectangle((x0, y0, x0 + cell - 5, y0 + cell - 5), fill=(shade, shade, 255), outline=(60, 60, 80))
            draw.text((x0 + 36, y0 + 36), str(value), fill=(0, 0, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)


def write_summary(path: Path, title: str, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([f"# {title}", "", *lines]) + "\n", encoding="utf-8")
