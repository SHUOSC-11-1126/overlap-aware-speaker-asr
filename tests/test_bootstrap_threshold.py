"""Tests for RQ44: bootstrap-aggregated threshold stability (experimental/frontier).

Pins the pure helpers: ``bootstrap_indices``, ``calibrate_threshold_at_spec``,
``percentile_interval``, ``out_of_bag_cpwer``. Also pins the lang-id entropy
detector primitives (RQ13/RQ16/RQ25 verbatim) and a smoke test that the
in-sample calibration on the real 77-window AISHELL-4 data reproduces RQ25's
threshold (0.38, sensitivity 35/37, specificity 37/40).

No Whisper / no audio needed. numpy + stdlib only.
"""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

# The RQ44 analysis script lives in results/frontier/ as a standalone module
# (no src. package). Import it via sys.path manipulation, mirroring the
# harness test_metadata_mode_s_detector / test_rq40_mode_s_corpus_specificity
# pattern.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_DIR = _PROJECT_ROOT / "results" / "frontier" / "bootstrap_threshold_stability"
sys.path.insert(0, str(_SCRIPT_DIR))

import bootstrap_threshold_analysis as rq44  # noqa: E402  (path-injected import)

AISHELL4_JSON = (
    _PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)


# ------------------------------------------------------------- bootstrap_indices
class TestBootstrapIndices(unittest.TestCase):
    def test_shape(self) -> None:
        idx = rq44.bootstrap_indices(77, 100, 42)
        self.assertEqual(idx.shape, (100, 77))

    def test_values_in_range(self) -> None:
        idx = rq44.bootstrap_indices(77, 100, 42)
        self.assertTrue(np.all(idx >= 0))
        self.assertTrue(np.all(idx < 77))

    def test_deterministic_given_seed(self) -> None:
        a = rq44.bootstrap_indices(10, 5, 42)
        b = rq44.bootstrap_indices(10, 5, 42)
        np.testing.assert_array_equal(a, b)

    def test_different_seeds_differ(self) -> None:
        a = rq44.bootstrap_indices(10, 5, 42)
        b = rq44.bootstrap_indices(10, 5, 7)
        self.assertFalse(np.array_equal(a, b))

    def test_each_row_length_equals_n(self) -> None:
        idx = rq44.bootstrap_indices(8, 3, 1)
        self.assertEqual(idx.shape, (3, 8))


# ------------------------------------------------------- calibrate_threshold_at_spec
class TestCalibrateThresholdAtSpec(unittest.TestCase):
    def test_separable_case(self) -> None:
        # negs in [0, 0.20], pos at 1.0/1.1 (within the 0..2.0 bit entropy
        # grid). A threshold just above 0.20 separates them: sens=1, spec=1.
        scores = np.array([0.0, 0.05, 0.10, 0.15, 0.20, 1.0, 1.1])
        labels = np.array([0, 0, 0, 0, 0, 1, 1])
        out = rq44.calibrate_threshold_at_spec(scores, labels)
        self.assertGreaterEqual(out["specificity"], 0.90 - 1e-9)
        self.assertEqual(out["sensitivity"], 1.0)
        self.assertEqual(out["tp"], 2)
        self.assertEqual(out["fn"], 0)

    def test_target_specificity_respected(self) -> None:
        scores = np.array([0., 0.1, 0.2, 0.3, 0.8, 0.9])
        labels = np.array([0, 0, 0, 0, 1, 1])
        out = rq44.calibrate_threshold_at_spec(scores, labels, target_spec=0.75)
        self.assertGreaterEqual(out["specificity"], 0.75 - 1e-9)

    def test_no_threshold_meets_target_falls_back(self) -> None:
        # Fully interleaved; target 0.99 unreachable -> fallback: flag nothing,
        # sens=0, spec=1.
        scores = np.array([0., 1., 2., 3.])
        labels = np.array([0, 1, 0, 1])
        out = rq44.calibrate_threshold_at_spec(scores, labels, target_spec=0.99)
        self.assertEqual(out["sensitivity"], 0.0)
        self.assertEqual(out["tp"], 0)
        self.assertEqual(out["fn"], 2)
        self.assertEqual(out["specificity"], 1.0)

    def test_empty_positives_safe(self) -> None:
        scores = np.array([0., 1., 2.])
        labels = np.array([0, 0, 0])
        out = rq44.calibrate_threshold_at_spec(scores, labels)
        self.assertEqual(out["sensitivity"], 0.0)
        self.assertGreaterEqual(out["specificity"], 0.90 - 1e-9)

    def test_bimodal_mode_s_scenario_prefers_higher_sensitivity(self) -> None:
        # Mirrors RQ25's Mode S mechanism: one low-entropy hallucinated window
        # (0.15) + one high-entropy hallucinated window (1.0); three clean
        # windows (0.0, 0.1, 0.2). At target_spec 2/3, dropping the threshold to
        # catch both positives (sens 1.0, FP=1, spec 2/3) beats staying high
        # (sens 0.5, spec 1.0).
        scores = np.array([0.0, 0.1, 0.2, 0.15, 1.0])
        labels = np.array([0, 0, 0, 1, 1])
        out = rq44.calibrate_threshold_at_spec(scores, labels, target_spec=2 / 3)
        self.assertEqual(out["sensitivity"], 1.0)
        self.assertEqual(out["tp"], 2)
        self.assertLess(out["threshold"], 0.38)

    def test_tie_break_lower_threshold(self) -> None:
        # negs 0,1 ; pos 5,6. Among thresholds giving sens=1 & spec=1 (t in
        # (1.0, 5.0]), the tie-break "lower threshold" selects the lowest grid
        # point > 1.0, i.e. 1.01.
        scores = np.array([0., 1., 5., 6.])
        labels = np.array([0, 0, 1, 1])
        out = rq44.calibrate_threshold_at_spec(scores, labels, target_spec=0.5)
        self.assertEqual(out["sensitivity"], 1.0)
        self.assertEqual(out["specificity"], 1.0)
        self.assertAlmostEqual(out["threshold"], 1.01, places=6)

    def test_returns_all_confusion_counts(self) -> None:
        scores = np.array([0.0, 0.5, 0.9, 1.0])
        labels = np.array([0, 0, 1, 1])
        out = rq44.calibrate_threshold_at_spec(scores, labels, target_spec=0.5)
        for key in ("threshold", "sensitivity", "specificity",
                    "tp", "fp", "tn", "fn"):
            self.assertIn(key, out)
        self.assertEqual(out["tp"] + out["fn"], 2)
        self.assertEqual(out["fp"] + out["tn"], 2)


# ------------------------------------------------------------- percentile_interval
class TestPercentileInterval(unittest.TestCase):
    def test_matches_numpy_percentile(self) -> None:
        vals = np.arange(101.0)  # 0..100
        lo, hi = rq44.percentile_interval(vals, 2.5, 97.5)
        self.assertAlmostEqual(lo, np.percentile(vals, 2.5))
        self.assertAlmostEqual(hi, np.percentile(vals, 97.5))

    def test_full_range(self) -> None:
        lo, hi = rq44.percentile_interval([1.0, 2.0, 3.0, 4.0, 5.0], 0, 100)
        self.assertEqual(lo, 1.0)
        self.assertEqual(hi, 5.0)

    def test_empty_returns_nan(self) -> None:
        lo, hi = rq44.percentile_interval([])
        self.assertTrue(math.isnan(lo))
        self.assertTrue(math.isnan(hi))

    def test_width_positive_for_spread(self) -> None:
        lo, hi = rq44.percentile_interval([0.0, 0.5, 1.0], 25, 75)
        self.assertGreater(hi, lo)

    def test_custom_percentiles(self) -> None:
        vals = np.arange(11.0)  # 0..10
        lo, hi = rq44.percentile_interval(vals, 25, 75)
        self.assertAlmostEqual(lo, np.percentile(vals, 25))
        self.assertAlmostEqual(hi, np.percentile(vals, 75))


# ------------------------------------------------------------- out_of_bag_cpwer
class TestOutOfBagCpwer(unittest.TestCase):
    def test_oob_excludes_in_bag(self) -> None:
        # n=5, in_bag = [0,0,1,1,2] -> OOB = {3,4}
        scores = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        mixed = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
        sep = np.array([2.0, 2.0, 2.0, 2.0, 2.0])
        out = rq44.out_of_bag_cpwer(scores, mixed, sep, threshold=0.4,
                                    in_bag_idx=np.array([0, 0, 1, 1, 2]))
        self.assertEqual(out["n_oob"], 2)
        # OOB windows 3,4: score 0.5 >= 0.4 -> flagged -> mixed (1.0)
        self.assertEqual(out["n_flagged_mixed"], 2)
        self.assertEqual(out["n_separated"], 0)
        self.assertAlmostEqual(out["cpwer"], 1.0)

    def test_routes_separated_when_below_threshold(self) -> None:
        scores = np.array([0.1, 0.1, 0.1, 0.1, 0.1])
        mixed = np.array([1.0] * 5)
        sep = np.array([2.0] * 5)
        out = rq44.out_of_bag_cpwer(scores, mixed, sep, threshold=0.4,
                                    in_bag_idx=np.array([0, 1, 2]))  # OOB={3,4}
        self.assertEqual(out["n_oob"], 2)
        self.assertEqual(out["n_separated"], 2)
        self.assertEqual(out["n_flagged_mixed"], 0)
        self.assertAlmostEqual(out["cpwer"], 2.0)

    def test_mixed_flagging_on_oob(self) -> None:
        # OOB windows have different scores.
        scores = np.array([0.1, 0.9, 0.1, 0.9, 0.1])
        mixed = np.array([1.0] * 5)
        sep = np.array([2.0] * 5)
        # in_bag = [0,1,2] -> OOB = {3,4}: score 0.9 (flag->mixed 1.0), 0.1 (sep 2.0)
        out = rq44.out_of_bag_cpwer(scores, mixed, sep, threshold=0.5,
                                    in_bag_idx=np.array([0, 1, 2]))
        self.assertEqual(out["n_oob"], 2)
        self.assertEqual(out["n_flagged_mixed"], 1)
        self.assertEqual(out["n_separated"], 1)
        self.assertAlmostEqual(out["cpwer"], 1.5)

    def test_all_in_bag_returns_nan(self) -> None:
        scores = np.array([0.5, 0.5])
        mixed = np.array([1.0, 1.0])
        sep = np.array([2.0, 2.0])
        out = rq44.out_of_bag_cpwer(scores, mixed, sep, threshold=0.4,
                                    in_bag_idx=np.array([0, 1, 0, 1]))
        self.assertEqual(out["n_oob"], 0)
        self.assertTrue(math.isnan(out["cpwer"]))
        self.assertEqual(out["n_flagged_mixed"], 0)

    def test_repeated_in_bag_covering_all(self) -> None:
        # in_bag repeats but covers all indices -> OOB empty.
        scores = np.array([0.5, 0.5, 0.5])
        mixed = np.array([1.0, 1.0, 1.0])
        sep = np.array([2.0, 2.0, 2.0])
        out = rq44.out_of_bag_cpwer(scores, mixed, sep, threshold=0.4,
                                    in_bag_idx=np.array([0, 1, 2, 0, 1, 2]))
        self.assertEqual(out["n_oob"], 0)

    def test_threshold_boundary_inclusive(self) -> None:
        # score == threshold is flagged (>= convention with EPS).
        scores = np.array([0.4, 0.4, 0.4])
        mixed = np.array([1.0, 1.0, 1.0])
        sep = np.array([3.0, 3.0, 3.0])
        out = rq44.out_of_bag_cpwer(scores, mixed, sep, threshold=0.4,
                                    in_bag_idx=np.array([0]))  # OOB={1,2}
        self.assertEqual(out["n_flagged_mixed"], 2)
        self.assertAlmostEqual(out["cpwer"], 1.0)


# ------------------------------------------------------------- detector primitives
class TestDetectorPrimitives(unittest.TestCase):
    def test_monoscript_chinese_zero_entropy(self) -> None:
        self.assertEqual(rq44.language_id_entropy("你好世界"), 0.0)

    def test_mixed_script_positive_entropy(self) -> None:
        self.assertGreater(rq44.language_id_entropy("你好AB"), 0.5)

    def test_empty_is_zero(self) -> None:
        self.assertEqual(rq44.language_id_entropy(""), 0.0)

    def test_whitespace_only_is_zero(self) -> None:
        self.assertEqual(rq44.language_id_entropy("   \n\t  "), 0.0)

    def test_script_category_han(self) -> None:
        self.assertEqual(rq44.script_category("你"), "Han")

    def test_script_category_space(self) -> None:
        self.assertEqual(rq44.script_category(" "), "Space")

    def test_max_across_speakers_empty_is_zero(self) -> None:
        self.assertEqual(rq44.max_across_speakers(
            {"separated_text_per_speaker": {"001-M": "", "002-M": "  "}}), 0.0)


# ------------------------------------------------------------- module constants
class TestModuleConstants(unittest.TestCase):
    def test_hypothesis_bounds(self) -> None:
        self.assertEqual(rq44.H44A_LO, 0.30)
        self.assertEqual(rq44.H44A_HI, 0.50)
        self.assertEqual(rq44.H44B_MAX_WIDTH, 0.20)
        self.assertEqual(rq44.H44C_MAX_CPWER, 1.10)

    def test_bootstrap_config(self) -> None:
        self.assertEqual(rq44.N_BOOT, 10000)
        self.assertEqual(rq44.SEED, 42)

    def test_target_specificity(self) -> None:
        self.assertEqual(rq44.TARGET_SPECIFICITY, 0.90)

    def test_threshold_grid_step(self) -> None:
        self.assertEqual(rq44.THRESHOLD_GRID[0], 0.00)
        self.assertEqual(rq44.THRESHOLD_GRID[-1], 2.00)
        self.assertEqual(len(rq44.THRESHOLD_GRID), 201)


# --------------------------------------------- in-sample reproduction (RQ25)
@unittest.skipUnless(AISHELL4_JSON.exists(), "AISHELL-4 validation JSON not present")
class TestInSampleReproduction(unittest.TestCase):
    """Validates calibrate_threshold_at_spec reproduces RQ25's in-sample
    threshold (0.38) and operating point (35/37 sensitivity, 37/40 specificity)
    on the real 77-window AISHELL-4 data."""

    @classmethod
    def setUpClass(cls) -> None:
        data = json.loads(AISHELL4_JSON.read_text(encoding="utf-8"))
        windows = data["windows"]
        cls.lang_ent = np.array(
            [rq44.max_across_speakers(w) for w in windows], dtype=float
        )
        cls.sep_cpwer = np.array(
            [float(w["always_separated_cpwer"]) for w in windows], dtype=float
        )
        cls.labels = (cls.sep_cpwer > 1.0).astype(int)
        cls.n = len(windows)

    def test_77_windows(self) -> None:
        self.assertEqual(self.n, 77)

    def test_37_hallucinated_40_clean(self) -> None:
        self.assertEqual(int(self.labels.sum()), 37)
        self.assertEqual(int((self.labels == 0).sum()), 40)

    def test_in_sample_threshold_is_038(self) -> None:
        out = rq44.calibrate_threshold_at_spec(self.lang_ent, self.labels)
        self.assertAlmostEqual(out["threshold"], 0.38, places=6)

    def test_in_sample_operating_point_matches_rq25(self) -> None:
        out = rq44.calibrate_threshold_at_spec(self.lang_ent, self.labels)
        self.assertAlmostEqual(out["sensitivity"], 35 / 37, places=4)
        self.assertAlmostEqual(out["specificity"], 37 / 40, places=4)
        self.assertEqual(out["tp"], 35)
        self.assertEqual(out["fp"], 3)


if __name__ == "__main__":
    unittest.main()
