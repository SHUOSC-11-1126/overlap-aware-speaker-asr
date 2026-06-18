"""Tests for the reference-free emotion-fidelity / separation-quality meter (experimental/frontier).

Pin the PURE, reference-free signals (no clean reference, no model): speaker-embedding self-consistency,
prosodic coherence, their combination into a [0,1] fidelity meter, and the validation summary that
(analysis-only) correlates the meter against the true emotion distortion and the leakage alpha.
"""
from __future__ import annotations

import unittest

import numpy as np

from src.emotion_fidelity_meter import (
    embedding_consistency,
    fidelity_meter,
    prosodic_consistency,
    summarize_meter,
)


class TestEmbeddingConsistency(unittest.TestCase):
    def test_identical_embeddings_max(self) -> None:
        embs = np.tile(np.array([1.0, 0.0, 0.0]), (5, 1))
        self.assertAlmostEqual(embedding_consistency(embs), 1.0, places=5)

    def test_two_clusters_lower(self) -> None:
        # half point one way, half the opposite -> centroid near zero -> low consistency
        embs = np.array([[1.0, 0.0]] * 3 + [[-1.0, 0.0]] * 3)
        self.assertLess(embedding_consistency(embs), 0.3)

    def test_single_window_is_one(self) -> None:
        self.assertAlmostEqual(embedding_consistency(np.array([[0.5, 0.5]])), 1.0, places=5)

    def test_empty_is_zero(self) -> None:
        self.assertEqual(embedding_consistency(np.zeros((0, 4))), 0.0)


class TestProsodicConsistency(unittest.TestCase):
    def test_constant_arousal_high(self) -> None:
        self.assertGreater(prosodic_consistency([0.5, 0.5, 0.5, 0.5]), 0.95)

    def test_variable_arousal_lower(self) -> None:
        hi = prosodic_consistency([0.5, 0.5, 0.5])
        lo = prosodic_consistency([0.0, 1.0, 0.0, 1.0])
        self.assertLess(lo, hi)

    def test_empty_safe(self) -> None:
        self.assertTrue(0.0 <= prosodic_consistency([]) <= 1.0)


class TestFidelityMeter(unittest.TestCase):
    def test_in_range_and_monotone(self) -> None:
        hi = fidelity_meter(0.95, 0.95)
        lo = fidelity_meter(0.2, 0.2)
        self.assertTrue(0.0 <= lo <= hi <= 1.0)
        self.assertGreater(hi, lo)

    def test_weighting(self) -> None:
        # weight on embedding term
        self.assertAlmostEqual(fidelity_meter(1.0, 0.0, w_embedding=1.0), 1.0, places=6)
        self.assertAlmostEqual(fidelity_meter(1.0, 0.0, w_embedding=0.0), 0.0, places=6)


class TestSummarizeMeter(unittest.TestCase):
    def _rows(self):
        # higher leakage alpha -> lower meter and higher true emotion distortion (meter should
        # anti-correlate with distortion: a good reference-free proxy).
        return [
            {"alpha": 0.0, "meter": 0.95, "emo_distortion": 0.05},
            {"alpha": 0.0, "meter": 0.90, "emo_distortion": 0.08},
            {"alpha": 0.3, "meter": 0.55, "emo_distortion": 0.40},
            {"alpha": 0.3, "meter": 0.50, "emo_distortion": 0.45},
        ]

    def test_meter_anticorrelates_distortion(self) -> None:
        s = summarize_meter(self._rows())
        self.assertLess(s["pearson_meter_distortion"], -0.8)

    def test_meter_anticorrelates_alpha(self) -> None:
        s = summarize_meter(self._rows())
        self.assertLess(s["pearson_meter_alpha"], -0.8)

    def test_keys_present(self) -> None:
        s = summarize_meter(self._rows())
        for k in ("n", "pearson_meter_distortion", "pearson_meter_alpha", "by_alpha"):
            self.assertIn(k, s)


if __name__ == "__main__":
    unittest.main()
