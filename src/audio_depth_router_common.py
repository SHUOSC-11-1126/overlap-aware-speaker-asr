from __future__ import annotations

import csv
import json
import math
import wave
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .config import PROJECT_ROOT


ROUTE_LABELS = ["mixed", "separated", "cleaned"]
METHOD_TO_LABEL = {
    "mixed_whisper": "mixed",
    "separated_whisper": "separated",
    "separated_whisper_cleaned": "cleaned",
}
LABEL_TO_METHOD = {value: key for key, value in METHOD_TO_LABEL.items()}
CER_COLUMNS = {
    "mixed": "mixed_cer",
    "separated": "separated_cer",
    "cleaned": "cleaned_cer",
}
TARGET_SHAPE = (3, 64, 96)


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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_wav_mono(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    if sample_width == 1:
        audio = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
        audio = (audio - 128.0) / 128.0
    elif sample_width == 2:
        audio = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    elif sample_width == 4:
        audio = np.frombuffer(frames, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width {sample_width} for {path}")
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio.astype(np.float32), sample_rate


def stft_magnitude(audio: np.ndarray, n_fft: int = 512, hop: int = 160) -> np.ndarray:
    if len(audio) < n_fft:
        audio = np.pad(audio, (0, n_fft - len(audio)))
    frame_count = 1 + max(0, (len(audio) - n_fft) // hop)
    windows = np.lib.stride_tricks.sliding_window_view(audio, n_fft)[::hop][:frame_count]
    window = np.hanning(n_fft).astype(np.float32)
    spec = np.fft.rfft(windows * window, axis=1)
    return np.abs(spec).T.astype(np.float32)


def resize_2d(arr: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    if arr.size == 0:
        return np.zeros(shape, dtype=np.float32)
    arr = normalize01(arr)
    image = Image.fromarray(np.uint8(arr * 255.0), mode="L")
    image = image.resize((shape[1], shape[0]), Image.Resampling.BILINEAR)
    return np.asarray(image, dtype=np.float32) / 255.0


def normalize01(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return np.zeros_like(arr, dtype=np.float32)
    lo = float(np.percentile(finite, 2))
    hi = float(np.percentile(finite, 98))
    if hi <= lo:
        hi = float(finite.max())
        lo = float(finite.min())
    if hi <= lo:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip((arr - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def pseudo_log_mel(audio: np.ndarray, sample_rate: int, height: int = 64, width: int = 96) -> np.ndarray:
    del sample_rate
    mag = stft_magnitude(audio)
    log_mag = np.log1p(mag)
    return resize_2d(log_mag, (height, width))


def frame_energy(audio: np.ndarray, n_fft: int = 512, hop: int = 160) -> np.ndarray:
    if len(audio) < n_fft:
        audio = np.pad(audio, (0, n_fft - len(audio)))
    frame_count = 1 + max(0, (len(audio) - n_fft) // hop)
    windows = np.lib.stride_tricks.sliding_window_view(audio, n_fft)[::hop][:frame_count]
    return np.sqrt(np.mean(np.square(windows), axis=1) + 1e-8).astype(np.float32)


def deployable_channels(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    log_mel = pseudo_log_mel(audio, sample_rate)
    mag = stft_magnitude(audio)
    log_mag = np.log1p(mag)
    norm_mag = normalize01(log_mag)
    high_energy_bins = (norm_mag > 0.62).mean(axis=0, keepdims=True)
    spectral_flux = np.diff(norm_mag, axis=1, prepend=norm_mag[:, :1])
    flux = np.mean(np.maximum(spectral_flux, 0.0), axis=0, keepdims=True)
    energy = frame_energy(audio)[None, :]
    energy_derivative = np.abs(np.diff(normalize01(energy), axis=1, prepend=energy[:, :1]))
    overlap_proxy = resize_2d(high_energy_bins + 0.5 * normalize01(energy), log_mel.shape)
    uncertainty_proxy = resize_2d(flux + energy_derivative, log_mel.shape)
    return np.stack([log_mel, overlap_proxy, uncertainty_proxy]).astype(np.float32)


def analysis_channels(audio: np.ndarray, sample_rate: int, spk1: np.ndarray, spk2: np.ndarray) -> np.ndarray:
    log_mel = pseudo_log_mel(audio, sample_rate)
    e1 = frame_energy(spk1)
    e2 = frame_energy(spk2)
    length = max(len(e1), len(e2))
    e1 = np.pad(e1, (0, length - len(e1)))
    e2 = np.pad(e2, (0, length - len(e2)))
    n1 = normalize01(e1)
    n2 = normalize01(e2)
    simultaneous = np.minimum(n1, n2)[None, :]
    dominance = (np.abs(e1 - e2) / (e1 + e2 + 1e-6))[None, :]
    return np.stack(
        [
            log_mel,
            resize_2d(simultaneous, log_mel.shape),
            resize_2d(dominance, log_mel.shape),
        ]
    ).astype(np.float32)


def save_map_preview(map_array: np.ndarray, output_path: Path, title: str = "") -> None:
    names = ["log-mel", "overlap/depth", "uncertainty/dominance"]
    panels = []
    for idx, channel in enumerate(map_array):
        arr = np.uint8(normalize01(channel) * 255.0)
        img = Image.fromarray(arr, mode="L").convert("RGB").resize((240, 160), Image.Resampling.BILINEAR)
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, 239, 20), fill=(0, 0, 0))
        draw.text((6, 4), names[idx], fill=(255, 255, 255))
        panels.append(img)
    canvas = Image.new("RGB", (720, 190), "white")
    for idx, panel in enumerate(panels):
        canvas.paste(panel, (idx * 240, 30))
    draw = ImageDraw.Draw(canvas)
    if title:
        draw.text((8, 8), title, fill=(0, 0, 0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)


def best_route_from_cers(row: dict[str, Any]) -> str:
    values = {label: float(row[CER_COLUMNS[label]]) for label in ROUTE_LABELS}
    return min(values, key=values.get)


def route_cer(row: dict[str, Any], route_label: str) -> float:
    return float(row[CER_COLUMNS[route_label]])


def macro_f1(y_true: list[str], y_pred: list[str], labels: Iterable[str] = ROUTE_LABELS) -> float:
    scores = []
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return float(sum(scores) / len(scores)) if scores else 0.0


def confusion_counts(y_true: list[str], y_pred: list[str], labels: list[str] = ROUTE_LABELS) -> list[list[int]]:
    return [[sum(1 for t, p in zip(y_true, y_pred) if t == a and p == b) for b in labels] for a in labels]


def draw_confusion_matrix(matrix: list[list[int]], output_path: Path, title: str) -> None:
    labels = ROUTE_LABELS
    cell = 84
    margin = 120
    canvas = Image.new("RGB", (margin + cell * 3 + 20, margin + cell * 3 + 30), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 15), title, fill=(0, 0, 0))
    max_value = max([value for row in matrix for value in row] + [1])
    for i, row in enumerate(matrix):
        draw.text((20, margin + i * cell + 30), labels[i], fill=(0, 0, 0))
        draw.text((margin + i * cell + 12, 70), labels[i], fill=(0, 0, 0))
        for j, value in enumerate(row):
            shade = 255 - int(180 * value / max_value)
            x0 = margin + j * cell
            y0 = margin + i * cell
            draw.rectangle((x0, y0, x0 + cell - 4, y0 + cell - 4), fill=(shade, shade, 255), outline=(50, 50, 80))
            draw.text((x0 + 34, y0 + 32), str(value), fill=(0, 0, 0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)


def draw_bar_chart(rows: list[dict[str, Any]], output_path: Path, label_key: str, value_key: str, title: str) -> None:
    width = 900
    height = 420
    margin_left = 240
    margin_bottom = 70
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 16), title, fill=(0, 0, 0))
    values = [float(row[value_key]) for row in rows]
    max_value = max(values + [1e-6])
    bar_h = max(18, int((height - 100) / max(1, len(rows))) - 8)
    for idx, row in enumerate(rows):
        y = 60 + idx * (bar_h + 8)
        value = float(row[value_key])
        bar_w = int((width - margin_left - 60) * value / max_value)
        draw.text((20, y + 3), str(row[label_key])[:34], fill=(0, 0, 0))
        draw.rectangle((margin_left, y, margin_left + bar_w, y + bar_h), fill=(70, 130, 180))
        draw.text((margin_left + bar_w + 8, y + 3), f"{value:.4f}", fill=(0, 0, 0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)


def summarize_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key, ""))
        counts[value] = counts.get(value, 0) + 1
    return counts
