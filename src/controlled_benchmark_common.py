from __future__ import annotations

import json
import math
import wave
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from .audio_depth_router_common import PROJECT_ROOT, read_csv, read_wav_mono, rel, write_csv
from .audio_depth_systematic_common import write_wav_mono
from .text_normalization import cer, normalize_asr_text


TABLE_DIR = PROJECT_ROOT / "results" / "tables"
FIGURE_DIR = PROJECT_ROOT / "results" / "figures"
MODEL_DIR = PROJECT_ROOT / "models"
CONTROLLED_ROOT = PROJECT_ROOT / "resources" / "controlled_route_sensitive_v1"
CONTROLLED_AUDIO_DIR = CONTROLLED_ROOT / "audio"
CONTROLLED_REF_DIR = CONTROLLED_ROOT / "references"
INVENTORY_CSV = TABLE_DIR / "controlled_utterance_inventory.csv"
VERIFICATION_PACK_CSV = TABLE_DIR / "controlled_verification_pack.csv"
MANIFEST_CSV = TABLE_DIR / "controlled_route_sensitive_manifest.csv"
TRANSCRIPTS_CSV = TABLE_DIR / "controlled_real_whisper_transcripts.csv"
CER_CSV = TABLE_DIR / "controlled_real_whisper_cer.csv"
RUNTIME_CSV = TABLE_DIR / "controlled_real_whisper_runtime.csv"
SENSITIVITY_CSV = TABLE_DIR / "controlled_route_sensitivity_summary.csv"
ROUTER_COMPARISON_CSV = TABLE_DIR / "controlled_audio_depth_router_comparison.csv"
ROUTER_PREDICTIONS_CSV = TABLE_DIR / "controlled_audio_depth_router_predictions.csv"


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        return round(wav.getnframes() / float(wav.getframerate()), 4)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def clean_route_text(text: str) -> str:
    norm = normalize_asr_text(text)
    # Light duplicate suppression for repeated Whisper loops.
    half = len(norm) // 2
    if half > 4 and norm[:half] == norm[half : half * 2]:
        return norm[:half]
    return norm


def mix_pair(
    audio_a: np.ndarray,
    audio_b: np.ndarray,
    sample_rate: int,
    overlap_ratio: float,
    dominance_type: str,
    duration: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    scale_a, scale_b = {
        "speaker_A_dominant": (1.0, 0.45),
        "speaker_B_dominant": (0.45, 1.0),
        "balanced": (0.78, 0.78),
    }.get(dominance_type, (0.78, 0.78))
    if duration == "medium":
        audio_a = np.concatenate([audio_a, np.zeros(int(0.12 * sample_rate), dtype=np.float32), audio_a])
        audio_b = np.concatenate([audio_b, np.zeros(int(0.12 * sample_rate), dtype=np.float32), audio_b])
    start_b = int(max(0, len(audio_a) * (1.0 - overlap_ratio)))
    total = max(len(audio_a), start_b + len(audio_b))
    spk1 = np.zeros(total, dtype=np.float32)
    spk2 = np.zeros(total, dtype=np.float32)
    spk1[: len(audio_a)] = audio_a * scale_a
    spk2[start_b : start_b + len(audio_b)] = audio_b * scale_b
    mixed = np.clip(spk1 + spk2, -0.95, 0.95)
    return mixed, spk1, spk2


def load_manifest_rows() -> list[dict[str, str]]:
    return read_csv(MANIFEST_CSV) if MANIFEST_CSV.exists() else []


def group_transcripts() -> dict[tuple[str, str], dict[str, str]]:
    rows = read_csv(TRANSCRIPTS_CSV) if TRANSCRIPTS_CSV.exists() else []
    return {(row["sample_id"], row["route"]): row for row in rows}


def route_gap(row: dict[str, Any]) -> float:
    vals = sorted(float(row[f"{route}_cer"]) for route in ["mixed", "separated", "cleaned"])
    return round(vals[1] - vals[0], 6)


def draw_bar(rows: list[dict[str, Any]], path: Path, label_key: str, value_key: str, title: str) -> None:
    width, height = 900, 420
    im = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(im)
    draw.text((24, 18), title, fill=(0, 0, 0))
    vals = [float(row[value_key]) for row in rows]
    max_val = max(vals + [1e-6])
    bar_w = max(28, int(760 / max(len(rows), 1)))
    for idx, row in enumerate(rows):
        x0 = 70 + idx * bar_w
        x1 = x0 + bar_w - 8
        y1 = 340
        y0 = y1 - int(250 * float(row[value_key]) / max_val)
        draw.rectangle((x0, y0, x1, y1), fill=(70, 120, 190))
        draw.text((x0, y0 - 16), f"{float(row[value_key]):.3f}", fill=(0, 0, 0))
        draw.text((x0, 350), str(row[label_key])[:12], fill=(0, 0, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)


def draw_line(rows: list[dict[str, Any]], path: Path, x_key: str, y_key: str, title: str) -> None:
    width, height = 900, 420
    im = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(im)
    draw.text((24, 18), title, fill=(0, 0, 0))
    xs = [float(row[x_key]) for row in rows]
    ys = [float(row[y_key]) for row in rows]
    if not xs or not ys:
        path.parent.mkdir(parents=True, exist_ok=True)
        im.save(path)
        return
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    if math.isclose(max_x, min_x):
        max_x += 1.0
    if math.isclose(max_y, min_y):
        max_y += 1.0
    pts = []
    for x, y in zip(xs, ys):
        px = 70 + int(760 * (x - min_x) / (max_x - min_x))
        py = 340 - int(250 * (y - min_y) / (max_y - min_y))
        pts.append((px, py))
    draw.line((70, 340, 840, 340), fill=(0, 0, 0))
    draw.line((70, 80, 70, 340), fill=(0, 0, 0))
    if len(pts) > 1:
        draw.line(pts, fill=(190, 70, 50), width=3)
    for pt in pts:
        draw.ellipse((pt[0] - 4, pt[1] - 4, pt[0] + 4, pt[1] + 4), fill=(190, 70, 50))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)


def compute_route_cers(reference: str, mixed: str, separated: str, cleaned: str) -> dict[str, float | str]:
    cers = {
        "mixed_cer": cer(reference, mixed),
        "separated_cer": cer(reference, separated),
        "cleaned_cer": cer(reference, cleaned),
    }
    route_values = {"mixed": cers["mixed_cer"], "separated": cers["separated_cer"], "cleaned": cers["cleaned_cer"]}
    oracle = min(route_values, key=route_values.get)
    vals = sorted(float(v) for v in route_values.values())
    return {
        **cers,
        "oracle_route": oracle,
        "oracle_cer": route_values[oracle],
        "route_gap": round(vals[1] - vals[0], 6),
        "separation_gain": round(float(cers["separated_cer"]) - float(cers["mixed_cer"]), 6),
    }
