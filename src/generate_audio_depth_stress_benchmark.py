from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np

from .audio_depth_router_common import PROJECT_ROOT, read_csv, read_wav_mono, rel, write_csv
from .audio_depth_systematic_common import STRESS_AUDIO_DIR, STRESS_MANIFEST_CSV, tile_to_length, write_wav_mono


OVERLAP_RATIOS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
DOMINANCE = [
    ("speaker_a_dominant", 1.0, 0.55),
    ("speaker_b_dominant", 0.55, 1.0),
    ("balanced", 0.85, 0.85),
    ("weak_target_speaker", 0.45, 1.0),
]
DURATIONS = [("short", 6.0), ("medium", 14.0), ("long", 24.0)]
STYLES = ["clean_turn_taking", "short_backchannel_overlap", "medium_overlap", "heavy_continuous_overlap", "opposite_position_debate"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate controlled AudioDepth stress benchmark audio.")
    parser.add_argument("--n-samples", type=int, default=150)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def source_pairs() -> list[tuple[Path, Path]]:
    manifest_path = PROJECT_ROOT / "results" / "tables" / "synthetic_split_manifest.csv"
    pairs = []
    for row in read_csv(manifest_path):
        spk1 = PROJECT_ROOT / row["spk1_path"]
        spk2 = PROJECT_ROOT / row["spk2_path"]
        if spk1.exists() and spk2.exists():
            pairs.append((spk1, spk2))
    return pairs


def build_sample(idx: int, rng: random.Random, pairs: list[tuple[Path, Path]]) -> dict[str, object]:
    ratio = OVERLAP_RATIOS[idx % len(OVERLAP_RATIOS)]
    dominance, gain_a, gain_b = DOMINANCE[(idx // len(OVERLAP_RATIOS)) % len(DOMINANCE)]
    duration_bucket, duration = DURATIONS[(idx // (len(OVERLAP_RATIOS) * len(DOMINANCE))) % len(DURATIONS)]
    style = STYLES[(idx // (len(OVERLAP_RATIOS) * len(DOMINANCE) * len(DURATIONS))) % len(STYLES)]
    spk1_path, spk2_path = pairs[idx % len(pairs)]
    spk1, sr = read_wav_mono(spk1_path)
    spk2, sr2 = read_wav_mono(spk2_path)
    if sr2 != sr:
        raise ValueError(f"Sample-rate mismatch: {spk1_path} vs {spk2_path}")
    length = int(duration * sr)
    a = tile_to_length(spk1, length)
    b = tile_to_length(spk2, length)
    offset = int((1.0 - ratio) * length)
    b_shifted = np.zeros(length, dtype=np.float32)
    if offset < length:
        b_shifted[offset:] = b[: length - offset]
    if ratio <= 0:
        b_shifted[:] = 0.0
    mixed = gain_a * a + gain_b * b_shifted
    max_abs = float(np.max(np.abs(mixed))) if mixed.size else 1.0
    if max_abs > 0.99:
        mixed = mixed / max_abs * 0.98
    sample_id = f"audio_depth_stress_v1_{idx + 1:04d}"
    mixed_path = STRESS_AUDIO_DIR / f"{sample_id}_mixed.wav"
    spk1_out = STRESS_AUDIO_DIR / f"{sample_id}_spk1.wav"
    spk2_out = STRESS_AUDIO_DIR / f"{sample_id}_spk2.wav"
    write_wav_mono(mixed_path, mixed, sr)
    write_wav_mono(spk1_out, gain_a * a, sr)
    write_wav_mono(spk2_out, gain_b * b_shifted, sr)
    split = "test" if idx % 5 == 0 else "dev" if idx % 5 == 1 else "train"
    return {
        "sample_id": sample_id,
        "benchmark": "audio_depth_stress_v1",
        "split": split,
        "overlap_ratio": ratio,
        "overlap_percent": int(ratio * 100),
        "dominance_condition": dominance,
        "speaker_a_gain": gain_a,
        "speaker_b_gain": gain_b,
        "duration_bucket": duration_bucket,
        "duration_sec": duration,
        "interruption_style": style,
        "sample_rate": sr,
        "mixed_path": rel(mixed_path),
        "spk1_path": rel(spk1_out),
        "spk2_path": rel(spk2_out),
        "source_spk1": rel(spk1_path),
        "source_spk2": rel(spk2_path),
        "random_seed": 42,
        "label_status": "needs_route_eval",
    }


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    pairs = source_pairs()
    if not pairs:
        raise FileNotFoundError("No synthetic source speaker pairs found.")
    rows = [build_sample(idx, rng, pairs) for idx in range(args.n_samples)]
    write_csv(STRESS_MANIFEST_CSV, rows)
    print(f"Wrote {len(rows)} stress samples to {rel(STRESS_MANIFEST_CSV)} and {rel(STRESS_AUDIO_DIR)}")


if __name__ == "__main__":
    main()
