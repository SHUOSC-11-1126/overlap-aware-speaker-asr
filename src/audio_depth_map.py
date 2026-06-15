from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np

from .audio_depth_router_common import PROJECT_ROOT, analysis_channels, deployable_channels, read_csv, read_wav_mono, rel, save_map_preview, write_csv
from .build_audio_depth_router_dataset import OUTPUT_CSV, build_dataset


METADATA_PATH = PROJECT_ROOT / "resources" / "audio_depth_maps" / "metadata_audio_depth_maps.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate AudioDepth-Router depth maps from WAV files.")
    parser.add_argument("--sample-id", default="")
    parser.add_argument("--sample-limit", type=int, default=0)
    parser.add_argument("--mode", default="deployable", choices=["deployable", "analysis", "logmel"])
    parser.add_argument("--all", action="store_true", help="Generate maps for the full synthetic split manifest.")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate maps even when files already exist.")
    parser.add_argument("--preview", action="store_true", default=True)
    return parser.parse_args()


def load_or_build_dataset(mode: str) -> list[dict[str, Any]]:
    if OUTPUT_CSV.exists():
        rows = read_csv(OUTPUT_CSV)
    else:
        rows = build_dataset(mode)
    for row in rows:
        row["representation_mode"] = mode
        row["map_path"] = f"resources/audio_depth_maps/{mode}/{row['sample_id']}.npy"
    return rows


def load_existing_metadata() -> dict[tuple[str, str], dict[str, Any]]:
    if not METADATA_PATH.exists():
        return {}
    return {(row.get("sample_id", ""), row.get("mode", "")): row for row in read_csv(METADATA_PATH)}


def generate_one(row: dict[str, Any], mode: str, preview: bool = True, overwrite: bool = False) -> dict[str, Any]:
    audio_path = PROJECT_ROOT / str(row["audio_path"])
    audio, sr = read_wav_mono(audio_path)
    if mode == "analysis":
        spk1_path = PROJECT_ROOT / str(row.get("spk1_path", ""))
        spk2_path = PROJECT_ROOT / str(row.get("spk2_path", ""))
        if not spk1_path.exists() or not spk2_path.exists():
            return {
                "sample_id": row["sample_id"],
                "mode": mode,
                "audio_path": row["audio_path"],
                "spk1_path": row.get("spk1_path", ""),
                "spk2_path": row.get("spk2_path", ""),
                "map_path": rel(PROJECT_ROOT / f"resources/audio_depth_maps/{mode}/{row['sample_id']}.npy"),
                "preview_path": "",
                "channels": "mixed_log_mel|simultaneous_activity|speaker_dominance",
                "label_type": "analysis_only",
                "status": "skipped_missing_tracks",
            }
        spk1, _ = read_wav_mono(spk1_path)
        spk2, _ = read_wav_mono(spk2_path)
        depth_map = analysis_channels(audio, sr, spk1, spk2)
        label_type = "analysis_only"
    elif mode == "logmel":
        depth_map = deployable_channels(audio, sr)[:1]
        label_type = "logmel_only"
    else:
        depth_map = deployable_channels(audio, sr)
        label_type = "deployable"

    map_path = PROJECT_ROOT / f"resources/audio_depth_maps/{mode}/{row['sample_id']}.npy"
    preview_path = PROJECT_ROOT / f"resources/audio_depth_maps/{mode}/{row['sample_id']}.png"
    map_path.parent.mkdir(parents=True, exist_ok=True)
    if map_path.exists() and not overwrite:
        return {
            "sample_id": row["sample_id"],
            "mode": mode,
            "audio_path": row["audio_path"],
            "spk1_path": row.get("spk1_path", ""),
            "spk2_path": row.get("spk2_path", ""),
            "map_path": rel(map_path),
            "preview_path": rel(preview_path) if preview_path.exists() else "",
            "channels": "log_mel"
            if mode == "logmel"
            else ("log_mel|overlap_proxy|uncertainty_proxy" if mode == "deployable" else "mixed_log_mel|simultaneous_activity|speaker_dominance"),
            "label_type": label_type,
            "status": "existing",
        }
    np.save(map_path, depth_map.astype(np.float32))
    if preview:
        save_map_preview(depth_map, preview_path, f"{row['sample_id']} ({mode}, best={row.get('best_route_label', '')})")
    return {
        "sample_id": row["sample_id"],
        "mode": mode,
        "audio_path": row["audio_path"],
        "spk1_path": row.get("spk1_path", ""),
        "spk2_path": row.get("spk2_path", ""),
        "map_path": rel(map_path),
        "preview_path": rel(preview_path) if preview_path.exists() else "",
        "channels": "log_mel"
        if mode == "logmel"
        else ("log_mel|overlap_proxy|uncertainty_proxy" if mode == "deployable" else "mixed_log_mel|simultaneous_activity|speaker_dominance"),
        "label_type": label_type,
        "status": "generated",
    }


def main() -> None:
    args = parse_args()
    rows = load_or_build_dataset(args.mode)
    if args.sample_id:
        rows = [row for row in rows if row["sample_id"] == args.sample_id]
    if args.all:
        pass
    if args.sample_limit:
        rows = rows[: args.sample_limit]
    metadata = [generate_one(row, args.mode, preview=args.preview, overwrite=args.overwrite) for row in rows]
    existing = load_existing_metadata()
    for row in metadata:
        existing[(row["sample_id"], row["mode"])] = row
    write_csv(
        METADATA_PATH,
        list(existing.values()),
        ["sample_id", "mode", "audio_path", "spk1_path", "spk2_path", "map_path", "preview_path", "channels", "label_type", "status"],
    )
    print(f"Wrote {len(metadata)} maps and metadata to {rel(METADATA_PATH)}")


if __name__ == "__main__":
    main()
