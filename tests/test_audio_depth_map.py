from __future__ import annotations

import numpy as np

from src.audio_depth_map import generate_one
from src.build_audio_depth_router_dataset import build_dataset


def test_audio_depth_map_shape() -> None:
    row = build_dataset("deployable")[0]
    metadata = generate_one(row, "deployable", preview=False)
    arr = np.load(metadata["map_path"])
    assert arr.shape == (3, 64, 96)
    assert np.isfinite(arr).all()


def test_analysis_map_is_analysis_only_when_tracks_exist() -> None:
    row = next(item for item in build_dataset("analysis") if item["spk1_path"] and item["spk2_path"])
    metadata = generate_one(row, "analysis", preview=False)
    assert metadata["label_type"] == "analysis_only"
    arr = np.load(metadata["map_path"])
    assert arr.shape == (3, 64, 96)
