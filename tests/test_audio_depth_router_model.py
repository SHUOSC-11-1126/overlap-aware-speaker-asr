from __future__ import annotations

import numpy as np

from src.audio_depth_router_common import ROUTE_LABELS, confusion_counts
from src.evaluate_audio_depth_router import load_model_predict


def test_cnn_fallback_prediction_does_not_crash_without_model() -> None:
    arrays = np.zeros((2, 3, 64, 96), dtype=np.float32)
    preds, status = load_model_predict("missing_for_test", arrays)
    assert preds == ["cleaned", "cleaned"]
    assert "fallback" in status


def test_confusion_matrix_shape() -> None:
    matrix = confusion_counts(["mixed", "cleaned"], ["mixed", "separated"])
    assert len(matrix) == len(ROUTE_LABELS)
    assert all(len(row) == len(ROUTE_LABELS) for row in matrix)
