from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from src.audio_depth_zoo_models import build_model


def test_cnn_depth_forward_shape() -> None:
    model = build_model("cnn_depth", input_channels=3, tabular_dim=0)
    x = torch.zeros((2, 3, 64, 96), dtype=torch.float32)
    logits = model(x)
    assert logits.shape == (2, 3)


def test_handcrafted_mlp_forward_shape() -> None:
    model = build_model("mlp_handcrafted", input_channels=0, tabular_dim=19)
    x = torch.zeros((4, 19), dtype=torch.float32)
    logits = model(x)
    assert logits.shape == (4, 3)


def test_hybrid_forward_shape() -> None:
    model = build_model("hybrid_late_fusion", input_channels=3, tabular_dim=19)
    x = torch.zeros((3, 3, 64, 96), dtype=torch.float32)
    tab = torch.zeros((3, 19), dtype=torch.float32)
    logits = model(x, tab)
    assert logits.shape == (3, 3)
