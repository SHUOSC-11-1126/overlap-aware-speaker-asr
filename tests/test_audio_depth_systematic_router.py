from __future__ import annotations

from src.audio_depth_systematic_common import feature_vector, metrics_for_predictions


def test_systematic_feature_vector_has_values() -> None:
    row = {key: 1.0 for key in ["duration", "mean_energy", "max_energy", "spectral_flux_mean", "spectral_flux_std", "overlap_proxy_mean", "overlap_proxy_max", "uncertainty_proxy_mean", "uncertainty_proxy_max", "energy_norm_mean", "mixed_segment_count", "separated_segment_count", "cleaned_removed_count", "length_ratio", "repetition_score", "method_disagreement_score", "separated_length", "mixed_length", "cleaned_length", "overlap_ratio"]}
    assert len(feature_vector(row)) >= 20


def test_systematic_metrics_for_predictions() -> None:
    preds = [{"true_route_label": "mixed", "predicted_route_label": "mixed", "predicted_cer": 0.1, "expected_cost": 1.0, "fallback_strategy": "none"}]
    metrics = metrics_for_predictions("demo", preds)
    assert metrics["routing_average_cer"] == 0.1
    assert metrics["classification_accuracy"] == 1.0
