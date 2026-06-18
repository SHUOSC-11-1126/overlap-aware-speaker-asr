"""Tests for the Emotional Separation Tax experiment (experimental/frontier).

Pin the PURE logic: the cross-talk leakage model, active-region detection, the emotion-recovery
benefit sign convention, per-overlap aggregation + crossover detection, and the emotion/CER
correlation. No Whisper, no librosa needed here (features are passed in as dicts / arrays).
"""
from __future__ import annotations

import unittest

import numpy as np

from src.emotion_separation_tax import (
    active_region,
    aggregate_tax,
    correlate_benefits,
    emotion_recovery_benefit,
    leak,
)


class TestLeak(unittest.TestCase):
    def test_alpha_zero_is_self(self) -> None:
        a = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        b = np.array([10.0, 10.0, 10.0], dtype=np.float32)
        np.testing.assert_allclose(leak(a, b, 0.0), a)

    def test_alpha_one_is_full_sum(self) -> None:
        a = np.array([1.0, 2.0], dtype=np.float32)
        b = np.array([3.0, 4.0], dtype=np.float32)
        np.testing.assert_allclose(leak(a, b, 1.0), a + b)

    def test_partial_leak(self) -> None:
        a = np.array([0.0, 0.0], dtype=np.float32)
        b = np.array([2.0, 4.0], dtype=np.float32)
        np.testing.assert_allclose(leak(a, b, 0.25), [0.5, 1.0])


class TestActiveRegion(unittest.TestCase):
    def test_basic(self) -> None:
        x = np.array([0, 0, 1, 2, 3, 0, 0], dtype=np.float32)
        self.assertEqual(active_region(x), (2, 5))

    def test_all_zero(self) -> None:
        self.assertEqual(active_region(np.zeros(5, dtype=np.float32)), (0, 0))

    def test_full(self) -> None:
        self.assertEqual(active_region(np.array([1, 1, 1], dtype=np.float32)), (0, 3))


class TestEmotionRecoveryBenefit(unittest.TestCase):
    """benefit = mixed_distortion - separated_distortion. >0 means separation RECOVERS emotion."""

    def test_separation_helps(self) -> None:
        # mixed badly distorted (0.8), separated close to reference (0.1) -> large positive benefit
        self.assertAlmostEqual(emotion_recovery_benefit(0.8, 0.1), 0.7, places=6)

    def test_separation_hurts(self) -> None:
        # mixed barely distorted (0.05), separation adds artifacts (0.2) -> negative benefit
        self.assertAlmostEqual(emotion_recovery_benefit(0.05, 0.2), -0.15, places=6)


class TestAggregateTax(unittest.TestCase):
    def _rows(self) -> list[dict]:
        # two overlaps; low overlap separation hurts, high overlap separation helps -> crossover
        return [
            {"overlap_ratio": 0.1, "alpha": 0.15, "emotion_benefit": -0.10, "gain_component_db": 1.0},
            {"overlap_ratio": 0.1, "alpha": 0.15, "emotion_benefit": -0.06, "gain_component_db": 1.2},
            {"overlap_ratio": 0.8, "alpha": 0.15, "emotion_benefit": 0.30, "gain_component_db": 2.0},
            {"overlap_ratio": 0.8, "alpha": 0.15, "emotion_benefit": 0.20, "gain_component_db": 1.8},
        ]

    def test_per_overlap_means(self) -> None:
        agg = aggregate_tax(self._rows())
        by = {r["overlap_ratio"]: r for r in agg["by_overlap"]}
        self.assertAlmostEqual(by[0.1]["mean_emotion_benefit"], -0.08, places=6)
        self.assertAlmostEqual(by[0.8]["mean_emotion_benefit"], 0.25, places=6)

    def test_crossover_detected(self) -> None:
        agg = aggregate_tax(self._rows())
        # sign flips from negative (low overlap) to positive (high overlap)
        self.assertTrue(agg["crossover_detected"])

    def test_no_crossover_when_all_positive(self) -> None:
        rows = [
            {"overlap_ratio": 0.1, "alpha": 0.0, "emotion_benefit": 0.1, "gain_component_db": 0.0},
            {"overlap_ratio": 0.8, "alpha": 0.0, "emotion_benefit": 0.3, "gain_component_db": 0.0},
        ]
        self.assertFalse(aggregate_tax(rows)["crossover_detected"])


class TestCorrelateBenefits(unittest.TestCase):
    def test_perfect_positive(self) -> None:
        em = [0.1, 0.2, 0.3, 0.4]
        cer = [0.2, 0.4, 0.6, 0.8]
        r = correlate_benefits(em, cer)
        self.assertGreater(r["pearson"], 0.99)

    def test_anticorrelated(self) -> None:
        em = [0.1, 0.2, 0.3, 0.4]
        cer = [0.8, 0.6, 0.4, 0.2]
        r = correlate_benefits(em, cer)
        self.assertLess(r["pearson"], -0.99)

    def test_degenerate_returns_nan_safe(self) -> None:
        r = correlate_benefits([1.0], [2.0])
        self.assertIn("pearson", r)


if __name__ == "__main__":
    unittest.main()
