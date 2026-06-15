from __future__ import annotations

from src.audio_depth_systematic_common import calibration_error


def test_calibration_error_bounds() -> None:
    preds = [{"confidence": 0.8, "true_route_label": "mixed", "predicted_route_label": "mixed"}]
    value = calibration_error(preds)
    assert 0.0 <= value <= 1.0
