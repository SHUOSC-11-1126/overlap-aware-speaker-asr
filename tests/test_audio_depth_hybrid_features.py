from __future__ import annotations

from src.audio_depth_zoo_common import FEATURES_CSV, build_hybrid_features_table


def test_hybrid_feature_table_has_required_columns() -> None:
    rows = build_hybrid_features_table()
    assert rows
    required = {
        "sample_id",
        "split",
        "overlap_tier",
        "best_route_label",
        "mixed_cer",
        "separated_cer",
        "cleaned_cer",
        "map_path_deployable",
        "map_path_logmel",
        "duration",
        "mean_energy",
        "spectral_flux_mean",
        "overlap_proxy_mean",
        "uncertainty_proxy_mean",
        "mixed_segment_count",
        "separated_segment_count",
        "cleaned_removed_count",
        "length_ratio",
        "repetition_score",
        "method_disagreement_score",
    }
    assert required.issubset(rows[0])
    assert FEATURES_CSV.exists()
