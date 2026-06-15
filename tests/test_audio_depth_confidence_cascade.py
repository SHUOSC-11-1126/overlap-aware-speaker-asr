from __future__ import annotations

import pytest

from src.audio_depth_confidence_cascade import router_v2_for_rows
from src.evaluate_audio_depth_model_zoo import predict_for_model
from src.build_audio_depth_router_dataset import build_dataset


def test_router_v2_fallback_when_table_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = build_dataset("deployable")[:2]
    import src.audio_depth_confidence_cascade as cascade

    original_exists = cascade.Path.exists

    def fake_exists(self):  # type: ignore[no-untyped-def]
        if self.name == "synthetic_split_routing_decisions.csv":
            return False
        return original_exists(self)

    monkeypatch.setattr(cascade.Path, "exists", fake_exists, raising=False)
    labels = router_v2_for_rows(rows)
    assert labels == ["mixed", "mixed"]


def test_missing_model_evaluation_falls_back_cleanly() -> None:
    rows = build_dataset("deployable")[:2]
    preds, status = predict_for_model("missing_audio_depth_zoo_model", rows)
    assert len(preds) == len(rows)
    assert status["status"] == "missing_model"
