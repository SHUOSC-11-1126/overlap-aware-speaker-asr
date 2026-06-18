"""Tests for the arousal -> ASR-difficulty probe (experimental/frontier).

Pin the PURE statistics: Pearson/Spearman, partial correlation (control for overlap), rank-AUC for
hallucination prediction, and within-stratum aggregation. No Whisper / librosa needed (the probe's
acoustic + decode values are passed in as plain rows).
"""
from __future__ import annotations

import unittest

import numpy as np

from src.arousal_asr_probe import (
    partial_correlation,
    pearson,
    rank_auc,
    spearman,
    summarize_probe,
)


class TestCorrelations(unittest.TestCase):
    def test_pearson_perfect(self) -> None:
        self.assertAlmostEqual(pearson([1, 2, 3, 4], [2, 4, 6, 8]), 1.0, places=6)

    def test_pearson_negative(self) -> None:
        self.assertAlmostEqual(pearson([1, 2, 3, 4], [4, 3, 2, 1]), -1.0, places=6)

    def test_pearson_degenerate_is_nan(self) -> None:
        self.assertTrue(np.isnan(pearson([1, 1, 1], [1, 2, 3])))

    def test_spearman_monotonic_nonlinear(self) -> None:
        # monotone but nonlinear -> Spearman 1.0 while Pearson < 1
        x = [1, 2, 3, 4, 5]
        y = [1, 4, 9, 16, 25]
        self.assertAlmostEqual(spearman(x, y), 1.0, places=6)
        self.assertLess(pearson(x, y), 1.0)


class TestPartialCorrelation(unittest.TestCase):
    def test_spurious_correlation_vanishes(self) -> None:
        # x and y are mostly driven by z (a strong common cause) plus small INDEPENDENT noise.
        # Their raw correlation is large (via z), but controlling for z it collapses toward 0.
        rng = np.random.default_rng(1)
        z = np.linspace(0, 1, 200)
        x = 3.0 * z + 0.02 * rng.normal(size=200)
        y = -2.0 * z + 0.02 * rng.normal(size=200)
        self.assertGreater(abs(pearson(x, y)), 0.9)            # strong raw (spurious) correlation
        self.assertLess(abs(partial_correlation(x, y, z)), 0.2)  # largely vanishes once z controlled

    def test_independent_signal_survives(self) -> None:
        rng = np.random.default_rng(0)
        z = rng.normal(size=200)
        common = rng.normal(size=200)
        # x and y share `common` which is independent of z -> partial corr stays high
        x = z + common
        y = z + common
        self.assertGreater(partial_correlation(x, y, z), 0.8)


class TestRankAuc(unittest.TestCase):
    def test_perfect_separation(self) -> None:
        scores = [0.1, 0.2, 0.8, 0.9]
        labels = [0, 0, 1, 1]
        self.assertAlmostEqual(rank_auc(scores, labels), 1.0, places=6)

    def test_reversed(self) -> None:
        scores = [0.9, 0.8, 0.2, 0.1]
        labels = [0, 0, 1, 1]
        self.assertAlmostEqual(rank_auc(scores, labels), 0.0, places=6)

    def test_single_class_is_nan(self) -> None:
        self.assertTrue(np.isnan(rank_auc([0.1, 0.2], [1, 1])))


class TestSummarizeProbe(unittest.TestCase):
    def _rows(self) -> list[dict]:
        # arousal rises with overlap; CER rises with overlap -> strong overall corr. But the
        # within-stratum jitters are ORTHOGONAL by construction (a=[+1,+1,-1,-1], c=[+1,-1,+1,-1]),
        # so once overlap is controlled, arousal and CER are uncorrelated: partial corr ~0.
        a_jit = [+1.0, +1.0, -1.0, -1.0]
        c_jit = [+1.0, -1.0, +1.0, -1.0]
        eps = 0.001
        rows = []
        for ov in (0.0, 0.3, 0.6, 0.9):
            for k in range(4):
                rows.append({
                    "overlap_ratio": ov,
                    "arousal": ov + eps * a_jit[k],
                    "cer": ov + eps * c_jit[k],
                    "max_compression_ratio": 1.5 + ov,
                    "hallucinated": int(ov >= 0.6),
                })
        return rows

    def test_overall_positive(self) -> None:
        s = summarize_probe(self._rows())
        self.assertGreater(s["pearson_arousal_cer"], 0.9)

    def test_partial_correlation_controls_overlap(self) -> None:
        s = summarize_probe(self._rows())
        # the arousal-CER link is fully explained by overlap here
        self.assertLess(abs(s["partial_pearson_controlling_overlap"]), 0.2)

    def test_keys_present(self) -> None:
        s = summarize_probe(self._rows())
        for k in ("pearson_arousal_cer", "spearman_arousal_cer",
                  "partial_pearson_controlling_overlap", "arousal_auc_hallucination",
                  "cr_auc_hallucination", "n", "by_overlap"):
            self.assertIn(k, s)


if __name__ == "__main__":
    unittest.main()
