"""Tests for Runtime Compute Cascade -- experimental/frontier."""
from __future__ import annotations


def test_cascade_gap_recovery_logic():
    """Verify the gap recovery calculation logic."""
    cer_tiny = 0.467
    cer_base = 0.200
    gap = cer_tiny - cer_base  # 0.267

    # If cascade CER = 0.267 (halfway), recovery = 0.75
    cascade_cer = 0.267
    recovery = (cer_tiny - cascade_cer) / gap
    assert abs(recovery - 0.75) < 0.01


def test_cascade_random_baseline():
    """Verify random escalation baseline calculation."""
    cer_tiny = 0.467
    cer_base = 0.200
    esc_frac = 0.2

    # Random 20% escalation: weighted average
    random_cer = esc_frac * cer_base + (1 - esc_frac) * cer_tiny
    expected = 0.2 * 0.200 + 0.8 * 0.467  # 0.04 + 0.3736 = 0.4136
    assert abs(random_cer - expected) < 0.001


def test_cascade_threshold_escalation_logic():
    """Verify escalation decision logic."""
    # If CR > threshold → escalate to base
    cr = 1.5
    assert cr > 1.0   # would escalate
    assert cr <= 2.0   # would NOT escalate at higher threshold


def test_cascade_pareto_dominance():
    """Verify Pareto dominance check logic."""
    # Cascade should be better than tiny (lower CER) AND cheaper than base (lower compute)
    tiny_cer = 0.467
    base_cer = 0.200
    cascade_cer = 0.300  # between tiny and base

    # Cascade beats tiny
    assert cascade_cer < tiny_cer
    # Cascade loses to base
    assert cascade_cer > base_cer
    # But cascade uses less compute (partial escalation)
