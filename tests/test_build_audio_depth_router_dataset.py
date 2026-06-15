from __future__ import annotations

from src.audio_depth_router_common import best_route_from_cers
from src.build_audio_depth_router_dataset import build_dataset


def test_dataset_manifest_required_columns() -> None:
    rows = build_dataset("deployable")
    assert rows
    required = {
        "sample_id",
        "split",
        "overlap_tier",
        "audio_path",
        "mixed_cer",
        "separated_cer",
        "cleaned_cer",
        "best_route_label",
        "label_source",
        "representation_mode",
        "map_path",
    }
    assert required.issubset(rows[0])


def test_best_route_label_from_cer() -> None:
    row = {"mixed_cer": 0.4, "separated_cer": 0.2, "cleaned_cer": 0.3}
    assert best_route_from_cers(row) == "separated"
    row = {"mixed_cer": 0.4, "separated_cer": 0.2, "cleaned_cer": 0.1}
    assert best_route_from_cers(row) == "cleaned"
