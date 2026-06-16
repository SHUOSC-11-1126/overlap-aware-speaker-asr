from __future__ import annotations

import unittest

from src.reference_free_qe import (
    decile_calibration,
    detection_auc,
    is_monotone_increasing,
    pearson,
    pool_separated_samples,
    spearman_corr,
)


class TestCorrelations(unittest.TestCase):
    def test_pearson_perfect_positive(self) -> None:
        self.assertAlmostEqual(pearson([1, 2, 3, 4], [2, 4, 6, 8]), 1.0, places=6)

    def test_pearson_degenerate(self) -> None:
        self.assertEqual(pearson([1, 1, 1], [1, 2, 3]), 0.0)
        self.assertEqual(pearson([5.0], [1.0]), 0.0)

    def test_spearman_monotone_nonlinear_is_one(self) -> None:
        # Spearman captures monotone (even nonlinear) relationships
        self.assertAlmostEqual(spearman_corr([1, 2, 3, 4], [1, 4, 9, 16]), 1.0, places=6)

    def test_spearman_handles_ties(self) -> None:
        # should not crash and stays in [-1, 1]
        r = spearman_corr([1, 1, 2, 3], [0.2, 0.3, 0.3, 0.9])
        self.assertGreaterEqual(r, -1.0)
        self.assertLessEqual(r, 1.0)


class TestDetectionAuc(unittest.TestCase):
    def test_higher_score_predicts_high_cer(self) -> None:
        scores = [0.5, 0.6, 5.0, 9.0]
        cers = [0.1, 0.2, 1.5, 2.0]  # threshold 1.0 => last two positive
        self.assertAlmostEqual(detection_auc(scores, cers, 1.0), 1.0)

    def test_no_positives_returns_half(self) -> None:
        self.assertEqual(detection_auc([1, 2, 3], [0.1, 0.2, 0.3], 1.0), 0.5)


class TestCalibration(unittest.TestCase):
    def test_monotone_buckets(self) -> None:
        scores = list(range(20))
        cers = [s / 20.0 for s in scores]  # CER increases with score
        bins = decile_calibration(scores, cers, n_bins=5)
        self.assertEqual(len(bins), 5)
        means = [b["mean_cer"] for b in bins]
        self.assertTrue(is_monotone_increasing(means))

    def test_empty(self) -> None:
        self.assertEqual(decile_calibration([], [], 5), [])

    def test_is_monotone_increasing(self) -> None:
        self.assertTrue(is_monotone_increasing([0.1, 0.1, 0.5, 0.9]))
        self.assertFalse(is_monotone_increasing([0.1, 0.5, 0.4]))


class TestPooling(unittest.TestCase):
    def test_pool_separated_skips_fallback_and_nan(self) -> None:
        rows = [
            {"config": "greedy", "cr_sep1": "1.0", "rep_sep1": "0", "nsp_sep1": "0.1", "cer_sep1": "0.2",
             "cr_sep2": "9.0", "rep_sep2": "20", "nsp_sep2": "0.5", "cer_sep2": "1.8"},
            {"config": "fallback", "cr_sep1": "1.0", "rep_sep1": "0", "nsp_sep1": "0.1", "cer_sep1": "0.3",
             "cr_sep2": "1.0", "rep_sep2": "0", "nsp_sep2": "0.1", "cer_sep2": "0.3"},
            {"config": "greedy", "cr_sep1": "2.0", "rep_sep1": "1", "nsp_sep1": "0.2", "cer_sep1": "nan",
             "cr_sep2": "2.0", "rep_sep2": "1", "nsp_sep2": "0.2", "cer_sep2": "0.4"},
        ]
        pool = pool_separated_samples(rows)
        # greedy row1 contributes 2 tracks; greedy row3 contributes 1 (other is NaN); fallback skipped
        self.assertEqual(len(pool["cer"]), 3)
        self.assertEqual(sorted(pool["cer"]), [0.2, 0.4, 1.8])


if __name__ == "__main__":
    unittest.main()
