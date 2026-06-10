from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT, load_config


TARGET_SR = 16000
TIER_ORDER = [
    "SyntheticNoOverlap",
    "SyntheticLightOverlap",
    "SyntheticMidOverlap",
    "SyntheticHeavyOverlap",
    "SyntheticOppositeOverlap",
]

TIER_SETTINGS = {
    "SyntheticNoOverlap": {"overlap_ratio": 0.0, "gap_sec": (0.20, 0.60)},
    "SyntheticLightOverlap": {"overlap_ratio": (0.10, 0.20)},
    "SyntheticMidOverlap": {"overlap_ratio": (0.30, 0.45)},
    "SyntheticHeavyOverlap": {"overlap_ratio": (0.50, 0.70)},
    "SyntheticOppositeOverlap": {"overlap_ratio": (0.80, 0.92)},
}

SPLITS = ("dev", "test")
SAMPLES_PER_SPLIT = 10


@dataclass
class AudioClip:
    filename: str
    samples: np.ndarray
    sample_rate: int

    @property
    def duration_sec(self) -> float:
        return float(len(self.samples)) / float(self.sample_rate)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a larger synthetic overlap split benchmark.")
    parser.add_argument("--num-per-tier", type=int, default=20, help="Samples to generate per tier.")
    return parser.parse_args()


def read_mono_audio(path: Path) -> AudioClip:
    import soundfile as sf
    from scipy.signal import resample_poly

    audio, sr = sf.read(path, always_2d=False)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    audio = audio.astype(np.float32)
    if sr != TARGET_SR:
        gcd = np.gcd(sr, TARGET_SR)
        up = TARGET_SR // gcd
        down = sr // gcd
        audio = resample_poly(audio, up, down).astype(np.float32)
        sr = TARGET_SR
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    if peak > 0:
        audio = audio / max(peak, 1.0)
    return AudioClip(filename=path.name, samples=audio, sample_rate=sr)


def list_snippets(snippets_dir: Path) -> tuple[list[Path], list[Path]]:
    con_files = sorted(snippets_dir.glob("con_*.wav"))
    pro_files = sorted(snippets_dir.glob("pro_*.wav"))
    if not con_files or not pro_files:
        raise FileNotFoundError(
            f"Missing snippet files in {snippets_dir.relative_to(PROJECT_ROOT)}; expected con_*.wav and pro_*.wav"
        )
    return con_files, pro_files


def choose_pair(con_files: list[Path], pro_files: list[Path], index: int) -> tuple[Path, Path]:
    con_path = con_files[index % len(con_files)]
    pro_path = pro_files[(index * 2) % len(pro_files)]
    return con_path, pro_path


def tier_overlap_ratio(tier: str, index: int) -> float:
    settings = TIER_SETTINGS[tier]
    value = settings["overlap_ratio"]
    if isinstance(value, tuple):
        low, high = value
        step = 0.0 if index == 0 else index / max(1, 19)
        return round(float(low + (high - low) * step), 4)
    return float(value)


def tier_gap_sec(tier: str, index: int) -> float:
    settings = TIER_SETTINGS[tier]
    if "gap_sec" not in settings:
        return 0.0
    low, high = settings["gap_sec"]
    step = 0.0 if index == 0 else index / max(1, 19)
    return round(float(low + (high - low) * step), 4)


def build_mixture(
    spk1: AudioClip,
    spk2: AudioClip,
    overlap_ratio: float,
    gap_sec: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    len1 = len(spk1.samples)
    len2 = len(spk2.samples)
    if overlap_ratio <= 0.0:
        start2 = len1 + int(round(gap_sec * TARGET_SR))
    else:
        overlap_samples = int(round(min(len1, len2) * overlap_ratio))
        start2 = max(0, len1 - overlap_samples)
    mixed_len = max(len1, start2 + len2)
    track1 = np.zeros(mixed_len, dtype=np.float32)
    track2 = np.zeros(mixed_len, dtype=np.float32)
    track1[:len1] = spk1.samples
    track2[start2 : start2 + len2] = spk2.samples
    mixed = track1 + track2
    peak = float(max(np.max(np.abs(mixed)), np.max(np.abs(track1)), np.max(np.abs(track2)), 1.0))
    if peak > 0.98:
        scale = 0.95 / peak
        track1 *= scale
        track2 *= scale
        mixed *= scale
    else:
        scale = 1.0
    return mixed, track1, track2, scale


def write_wav(path: Path, audio: np.ndarray, sr: int = TARGET_SR) -> None:
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, audio, sr, subtype="PCM_16")


def make_reference(
    sample_id: str,
    tier: str,
    split: str,
    overlap_ratio: float,
    con_source: str,
    pro_source: str,
    mixed_path: Path,
    spk1_path: Path,
    spk2_path: Path,
) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "tier": tier,
        "split": split,
        "overlap_level": tier,
        "overlap_ratio": overlap_ratio,
        "reference_type": "synthetic_placeholder",
        "status": "draft",
        "source_files": [con_source, pro_source],
        "speaker_1_label": "con",
        "speaker_2_label": "pro",
        "speaker_1_source": con_source,
        "speaker_2_source": pro_source,
        "mixed_audio_path": mixed_path.relative_to(PROJECT_ROOT).as_posix(),
        "spk1_audio_path": spk1_path.relative_to(PROJECT_ROOT).as_posix(),
        "spk2_audio_path": spk2_path.relative_to(PROJECT_ROOT).as_posix(),
        "speaker_1_text": "",
        "speaker_2_text": "",
        "full_text": "",
        "text": "",
        "notes": "Synthetic benchmark generated from snippets. Transcripts are pending.",
    }


def split_for_index(index: int) -> str:
    return SPLITS[0] if index < SAMPLES_PER_SPLIT else SPLITS[1]


def sample_index_within_split(index: int) -> int:
    return index % SAMPLES_PER_SPLIT


def main() -> None:
    args = parse_args()
    _ = load_config()

    snippets_dir = PROJECT_ROOT / "resources" / "snippets"
    con_files, pro_files = list_snippets(snippets_dir)

    base_audio_dir = PROJECT_ROOT / "resources" / "synthetic_overlap_v2" / "audio"
    base_ref_dir = PROJECT_ROOT / "resources" / "synthetic_overlap_v2" / "references"
    base_audio_dir.mkdir(parents=True, exist_ok=True)
    base_ref_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {tier: 0 for tier in TIER_ORDER}
    if args.num_per_tier != 20:
        print(f"warning: num-per-tier={args.num_per_tier} requested; split plan is designed for 20 per tier")

    for tier in TIER_ORDER:
        for idx in range(args.num_per_tier):
            con_path, pro_path = choose_pair(con_files, pro_files, idx)
            spk1 = read_mono_audio(con_path)
            spk2 = read_mono_audio(pro_path)
            overlap_ratio = tier_overlap_ratio(tier, idx)
            gap_sec = tier_gap_sec(tier, idx)
            mixed, track1, track2, scale = build_mixture(spk1, spk2, overlap_ratio, gap_sec=gap_sec)

            split = split_for_index(idx)
            split_index = sample_index_within_split(idx) + 1
            sample_id = f"{tier}_{split}_{split_index:02d}"
            tier_dir = base_audio_dir / tier
            mixed_path = tier_dir / f"{sample_id}_mixed.wav"
            spk1_path = tier_dir / f"{sample_id}_spk1.wav"
            spk2_path = tier_dir / f"{sample_id}_spk2.wav"
            reference_path = base_ref_dir / f"{sample_id}.json"

            write_wav(mixed_path, mixed)
            write_wav(spk1_path, track1)
            write_wav(spk2_path, track2)

            reference = make_reference(
                sample_id=sample_id,
                tier=tier,
                split=split,
                overlap_ratio=overlap_ratio,
                con_source=con_path.name,
                pro_source=pro_path.name,
                mixed_path=mixed_path,
                spk1_path=spk1_path,
                spk2_path=spk2_path,
            )
            reference["peak_scale"] = scale
            reference["mixed_duration_sec"] = round(len(mixed) / TARGET_SR, 4)
            reference_path.write_text(json.dumps(reference, ensure_ascii=False, indent=2), encoding="utf-8")

            manifest_rows.append(
                {
                    "sample_id": sample_id,
                    "tier": tier,
                    "split": split,
                    "overlap_level": tier,
                    "overlap_ratio": overlap_ratio,
                    "con_source": con_path.name,
                    "pro_source": pro_path.name,
                    "mixed_path": mixed_path.relative_to(PROJECT_ROOT).as_posix(),
                    "spk1_path": spk1_path.relative_to(PROJECT_ROOT).as_posix(),
                    "spk2_path": spk2_path.relative_to(PROJECT_ROOT).as_posix(),
                    "reference_path": reference_path.relative_to(PROJECT_ROOT).as_posix(),
                    "mixed_duration_sec": round(len(mixed) / TARGET_SR, 4),
                    "sample_rate": TARGET_SR,
                }
            )
            counts[tier] += 1

    manifest_path = PROJECT_ROOT / "results" / "tables" / "synthetic_split_manifest.csv"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sample_id",
        "tier",
        "split",
        "overlap_level",
        "overlap_ratio",
        "con_source",
        "pro_source",
        "mixed_path",
        "spk1_path",
        "spk2_path",
        "reference_path",
        "mixed_duration_sec",
        "sample_rate",
    ]
    with manifest_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Wrote synthetic split manifest: {manifest_path.relative_to(PROJECT_ROOT)}")
    for tier in TIER_ORDER:
        print(f"{tier}: {counts[tier]} samples")


if __name__ == "__main__":
    main()
