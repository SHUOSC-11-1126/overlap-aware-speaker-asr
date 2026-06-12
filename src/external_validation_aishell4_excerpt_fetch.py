from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .external_validation_audio_excerpt_staging_plan import (
    apply_staging_plan_to_mapping,
    load_slice_mapping,
    write_mapping_artifacts,
)
from .external_validation_license_confirmation import CONFIRMED_LICENSE_STATUS


HF_FLAC_URL = (
    "https://huggingface.co/datasets/AISHELL/AISHELL-4/resolve/main/test/wav/S_R004S03C01.flac"
)
HF_SOURCE_PATH = "test/wav/S_R004S03C01.flac"
EXCERPT_SECONDS = 30


def load_slice_mapping_local() -> dict[str, Any]:
    return load_slice_mapping()


def flac_cache_path() -> Path:
    return PROJECT_ROOT / "resources" / "external_sanity_check" / "aishell4" / "S_R004S03C01.flac"


def audio_target_path(mapping: dict[str, Any]) -> Path:
    return PROJECT_ROOT / str(mapping.get("audio_path", ""))


def reference_target_path(mapping: dict[str, Any]) -> Path:
    return PROJECT_ROOT / str(mapping.get("reference_path", ""))


def download_flac(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        return
    request = urllib.request.Request(
        HF_FLAC_URL,
        headers={"User-Agent": "overlap-aware-speaker-asr-external-sanity-check"},
    )
    with urllib.request.urlopen(request, timeout=600) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def convert_excerpt(flac_path: Path, wav_path: Path, seconds: int = EXCERPT_SECONDS) -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required to convert AISHELL-4 flac excerpt to wav")
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(flac_path),
            "-t",
            str(seconds),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(wav_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def build_reference_payload(mapping: dict[str, Any], seconds: int = EXCERPT_SECONDS) -> dict[str, Any]:
    return {
        "slice_id": str(mapping.get("slice_id", "")),
        "dataset_name": str(mapping.get("dataset_name", "AISHELL-4")),
        "label": "external/sanity-check",
        "license_id": str(mapping.get("license_id", "CC BY-SA 4.0")),
        "source_path": HF_SOURCE_PATH,
        "source_url": HF_FLAC_URL,
        "excerpt_seconds": seconds,
        "speaker_schema": mapping.get("speaker_schema", {}),
        "segments": [
            {
                "speaker": "meeting_mix",
                "start": 0.0,
                "end": float(seconds),
                "text": "",
                "transcript_status": "pending_external_alignment",
            }
        ],
        "staging_status": "audio_excerpt_staged",
        "staging_note": (
            "Real AISHELL-4 test-set excerpt staged from HuggingFace. "
            "Transcript alignment remains external/sanity-check only; not gold benchmark."
        ),
    }


def fetch_excerpt(mapping: dict[str, Any] | None = None, seconds: int = EXCERPT_SECONDS) -> dict[str, str]:
    active_mapping = mapping or load_slice_mapping_local()
    if not active_mapping:
        raise FileNotFoundError("external_validation_slice_mapping.json is missing")
    license_status = str(active_mapping.get("license_status", ""))
    if license_status != CONFIRMED_LICENSE_STATUS:
        raise RuntimeError(
            f"License must be {CONFIRMED_LICENSE_STATUS} before fetching AISHELL-4 audio; got {license_status!r}"
        )

    flac_path = flac_cache_path()
    wav_path = audio_target_path(active_mapping)
    reference_path = reference_target_path(active_mapping)

    download_flac(flac_path)
    convert_excerpt(flac_path, wav_path, seconds=seconds)
    reference_path.write_text(
        json.dumps(build_reference_payload(active_mapping, seconds=seconds), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    updated_mapping = apply_staging_plan_to_mapping(active_mapping)
    updated_mapping["staging_status"] = "audio_excerpt_staged"
    updated_mapping["mapping_status"] = "audio_and_reference_staged"
    updated_mapping["source_path"] = HF_SOURCE_PATH
    updated_mapping["source_url"] = HF_FLAC_URL
    updated_mapping["scaffold_note"] = (
        f"Staged {seconds}s mono excerpt from AISHELL-4 {HF_SOURCE_PATH} via HuggingFace."
    )
    write_mapping_artifacts(updated_mapping)

    return {
        "audio_path": str(wav_path.relative_to(PROJECT_ROOT)),
        "reference_path": str(reference_path.relative_to(PROJECT_ROOT)),
        "staging_status": updated_mapping["staging_status"],
        "flac_cache_path": str(flac_path.relative_to(PROJECT_ROOT)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch and stage a short AISHELL-4 test excerpt for external/sanity-check."
    )
    parser.add_argument(
        "--seconds",
        type=int,
        default=EXCERPT_SECONDS,
        help="Excerpt length in seconds (default: 30).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _ = load_config()
    result = fetch_excerpt(seconds=args.seconds)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
