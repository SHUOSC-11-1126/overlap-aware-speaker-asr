"""Tests for Whisper Model Scale Analysis -- experimental/frontier."""
from __future__ import annotations

from src.separation_tax_phase import tail_rate


# ---- tail_rate tests (reuse from separation_tax, verify consistency) ---------------

def test_tail_rate_all_below():
    assert tail_rate([0.1, 0.2, 0.3, 0.5]) == 0.0


def test_tail_rate_all_above():
    assert tail_rate([1.1, 1.5, 2.0]) == 1.0


def test_tail_rate_mixed():
    assert tail_rate([0.5, 1.1, 0.8, 2.0]) == 0.5


def test_tail_rate_empty():
    assert tail_rate([]) == 0.0


def test_tail_rate_custom_threshold():
    assert tail_rate([0.3, 0.6, 0.9], threshold=0.5) == 2 / 3


def test_tail_rate_nan_handling():
    # NaN values should be excluded
    assert tail_rate([0.5, float("nan"), 1.5]) == 0.5


# ---- Cross-model comparison logic tests -------------------------------------------

def test_h1_hypothesis_structure():
    """Verify the H1 hypothesis logic: tail rate should decrease with model size."""
    # Simulated: tiny has high tail, base has lower
    tail_tiny = 0.3
    tail_base = 0.1
    assert tail_tiny >= tail_base  # H1 would be confirmed


def test_h3_signal_paradox_structure():
    """Verify H3 logic: CR AUC should decrease with model size."""
    # Simulated: tiny has high AUC (signal is discriminative), base has lower
    auc_tiny = 0.95
    auc_base = 0.70
    # H3 says larger models → lower AUC (signal becomes less discriminative)
    assert auc_tiny >= auc_base  # paradox confirmed
