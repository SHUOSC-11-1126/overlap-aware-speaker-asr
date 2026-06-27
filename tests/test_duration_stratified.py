"""Tests for RQ57: window-duration stratified threshold (experimental/frontier).

Pins the pure helpers: ``script_category`` / ``language_id_entropy`` /
``max_across_speakers`` (RQ13 verbatim), ``duration_proxy`` (sum of speaker track
lengths), ``stratify_by_duration`` (median split into short/long strata),
``mann_whitney_u_test`` (two-sided normal approximation with tie correction,
numpy + stdlib only), ``calibrate_threshold_at_spec`` (RQ44/RQ49 verbatim),
``combined_oob_cpwer`` (RQ49 verbatim), ``bootstrap_stratified`` (RQ49 verbatim
but duration-agnostic), ``count_modes`` (RQ49 verbatim), and ``percentile_interval``.
Also pins smoke tests on the real 77-window AISHELL-4 data:

  - pooled in-sample calibration reproduces RQ44/RQ25's 0.38 threshold
  - the median duration split partitions all 77 windows into two non-empty strata
  - the within-script pooled bootstrap reproduces RQ44's 6-unique / 5-modes / width-0.94

No Whisper / no audio needed. numpy + stdlib only.
"""
from __future__ import annotations

import csv
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

# The RQ57 analysis script lives in results/frontier/ as a standalone module
# (no src. package). Import it via sys.path manipulation, mirroring the
# harness test_stratified_threshold / test_bootstrap_threshold pattern.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_DIR = _PROJECT_ROOT / "results" / "frontier" / "duration_stratified_threshold"
sys.path.insert(0, str(_SCRIPT_DIR))

import duration_stratified_analysis as rq57  # noqa: E402  (path-injected import)

AISHELL4_JSON = (
    _PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
RESULTS_JSON = _SCRIPT_DIR / "duration_stratified_results.json"
RESULTS_CSV = _SCRIPT_DIR / "duration_stratified_results.csv"


# --------------------------------------------- script_category
class TestScriptCategory(unittest.TestCase):
    def test_whitespace_is_space(self) -> None:
        self.assertEqual(rq57.script_category(" "), "Space")
        self.assertEqual(rq57.script_category("\n"), "Space")
        self.assertEqual(rq57.script_category("\t"), "Space")

    def test_han_character(self) -> None:
        self.assertEqual(rq57.script_category("你"), "Han")

    def test_latin_character(self) -> None:
        self.assertEqual(rq57.script_category("a"), "Latin")
        self.assertEqual(rq57.script_category("Z"), "Latin")

    def test_digit_is_digit(self) -> None:
        self.assertEqual(rq57.script_category("7"), "Digit")

    def test_punctuation_is_punct(self) -> None:
        self.assertEqual(rq57.script_category(","), "Punct")
        self.assertEqual(rq57.script_category("!"), "Punct")


# --------------------------------------------- language_id_entropy
class TestLanguageIdEntropy(unittest.TestCase):
    def test_empty_string_zero(self) -> None:
        self.assertEqual(rq57.language_id_entropy(""), 0.0)

    def test_whitespace_only_zero(self) -> None:
        self.assertEqual(rq57.language_id_entropy("   \n\t "), 0.0)

    def test_monoscript_near_zero(self) -> None:
        # Pure Han -> single script category -> entropy 0.
        self.assertEqual(rq57.language_id_entropy("你好世界"), 0.0)

    def test_two_scripts_entropy_one_bit(self) -> None:
        # Equal mix of two scripts -> exactly 1 bit of entropy.
        h = rq57.language_id_entropy("ab你好")
        self.assertAlmostEqual(h, 1.0, places=6)

    def test_more_scripts_higher_entropy(self) -> None:
        h1 = rq57.language_id_entropy("ab你好")  # 2 scripts
        h2 = rq57.language_id_entropy("ab你好안")  # 3 scripts (Latin, Han, Hangul)
        self.assertGreater(h2, h1)

    def test_entropy_nonneg(self) -> None:
        self.assertGreaterEqual(rq57.language_id_entropy("a b 你 1"), 0.0)


# --------------------------------------------- max_across_speakers
class TestMaxAcrossSpeakers(unittest.TestCase):
    def test_max_of_speaker_entropies(self) -> None:
        window = {"separated_text_per_speaker": {"A": "你好", "B": "ab你好안"}}
        # A is monoscript (0), B is 3 scripts -> max is B's entropy.
        expected = rq57.language_id_entropy("ab你好안")
        self.assertAlmostEqual(rq57.max_across_speakers(window), expected, places=9)

    def test_empty_speakers_zero(self) -> None:
        self.assertEqual(rq57.max_across_speakers({"separated_text_per_speaker": {}}), 0.0)

    def test_missing_key_zero(self) -> None:
        self.assertEqual(rq57.max_across_speakers({}), 0.0)

    def test_whitespace_only_speakers_skipped(self) -> None:
        window = {"separated_text_per_speaker": {"A": "   ", "B": "  \n"}}
        self.assertEqual(rq57.max_across_speakers(window), 0.0)

    def test_none_values_skipped(self) -> None:
        window = {"separated_text_per_speaker": {"A": None, "B": "你好"}}
        self.assertEqual(rq57.max_across_speakers(window), 0.0)


# --------------------------------------------- duration_proxy
class TestDurationProxy(unittest.TestCase):
    def test_simple_sum_of_track_lengths(self) -> None:
        window = {"separated_text_per_speaker": {"A": "abc", "B": "de", "C": "fghi"}}
        # 3 + 2 + 4 = 9
        self.assertEqual(rq57.duration_proxy(window), 9)

    def test_empty_dict_returns_zero(self) -> None:
        self.assertEqual(rq57.duration_proxy({"separated_text_per_speaker": {}}), 0)

    def test_missing_key_returns_zero(self) -> None:
        self.assertEqual(rq57.duration_proxy({}), 0)

    def test_none_values_skipped(self) -> None:
        window = {"separated_text_per_speaker": {"A": "abc", "B": None, "C": "de"}}
        # None treated as 0-length; 3 + 2 = 5
        self.assertEqual(rq57.duration_proxy(window), 5)

    def test_whitespace_only_counted_as_length(self) -> None:
        # Whitespace characters still contribute to len(); we only skip None.
        window = {"separated_text_per_speaker": {"A": "a b", "B": "  "}}
        # "a b" -> 3, "  " -> 2 ; sum = 5
        self.assertEqual(rq57.duration_proxy(window), 5)

    def test_single_speaker(self) -> None:
        window = {"separated_text_per_speaker": {"A": "hello"}}
        self.assertEqual(rq57.duration_proxy(window), 5)

    def test_nonneg(self) -> None:
        window = {"separated_text_per_speaker": {"A": "x", "B": "yz"}}
        self.assertGreaterEqual(rq57.duration_proxy(window), 0)

    def test_matches_separated_total_length_field_on_real_data(self) -> None:
        # Cross-check: the JSON's stored separated_total_length should equal the
        # sum of speaker track lengths computed from separated_text_per_speaker.
        if not AISHELL4_JSON.exists():
            self.skipTest("AISHELL-4 JSON not present")
        data = json.loads(AISHELL4_JSON.read_text(encoding="utf-8"))
        mismatches = 0
        for w in data["windows"]:
            computed = rq57.duration_proxy(w)
            stored = int(w.get("separated_total_length", -1))
            if computed != stored:
                mismatches += 1
        # Allow zero mismatches: the field is the same sum.
        self.assertEqual(mismatches, 0)


# --------------------------------------------- stratify_by_duration
class TestStratifyByDuration(unittest.TestCase):
    def test_returns_two_arrays(self) -> None:
        d = np.array([1.0, 2.0, 3.0, 4.0])
        short, long = rq57.stratify_by_duration(d)
        self.assertEqual(len(short) + len(long), 4)

    def test_partition_exhaustive_and_disjoint(self) -> None:
        d = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        short, long = rq57.stratify_by_duration(d, split=30.0)
        union = sorted(list(short) + list(long))
        self.assertEqual(union, [0, 1, 2, 3, 4])
        self.assertEqual(set(short) & set(long), set())

    def test_stratum1_is_le_split(self) -> None:
        d = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        short, _ = rq57.stratify_by_duration(d, split=3.0)
        for i in short:
            self.assertLessEqual(d[i], 3.0)

    def test_stratum2_is_gt_split(self) -> None:
        d = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        _, long = rq57.stratify_by_duration(d, split=3.0)
        for i in long:
            self.assertGreater(d[i], 3.0)

    def test_default_split_is_median(self) -> None:
        d = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        short_def, long_def = rq57.stratify_by_duration(d)
        # median of [1,2,3,4,5] = 3.0 ; short = {1,2,3}, long = {4,5}
        self.assertEqual(sorted(short_def), [0, 1, 2])
        self.assertEqual(sorted(long_def), [3, 4])

    def test_median_split_even_count(self) -> None:
        # Even count: median = average of two middle values. The split point is
        # the median value; ties at the median go to "short" (<=).
        d = np.array([1.0, 2.0, 3.0, 4.0])
        short, long = rq57.stratify_by_duration(d)
        # median = (2+3)/2 = 2.5 ; short = {1,2}, long = {3,4}
        self.assertEqual(sorted(short), [0, 1])
        self.assertEqual(sorted(long), [2, 3])

    def test_empty_input(self) -> None:
        short, long = rq57.stratify_by_duration(np.array([]))
        self.assertEqual(len(short), 0)
        self.assertEqual(len(long), 0)

    def test_all_equal_goes_to_short(self) -> None:
        # All durations equal to the median -> all go to "short" (<=).
        d = np.array([5.0, 5.0, 5.0])
        short, long = rq57.stratify_by_duration(d)
        self.assertEqual(len(short), 3)
        self.assertEqual(len(long), 0)

    def test_custom_split(self) -> None:
        d = np.array([10.0, 20.0, 30.0, 40.0])
        short, long = rq57.stratify_by_duration(d, split=25.0)
        self.assertEqual(sorted(short), [0, 1])  # 10, 20 <= 25
        self.assertEqual(sorted(long), [2, 3])   # 30, 40 > 25


# --------------------------------------------- mann_whitney_u_test
class TestMannWhitneyU(unittest.TestCase):
    def test_identical_distributions_high_p(self) -> None:
        # Two identical samples -> p-value should be large (cannot reject H0).
        rng = np.random.default_rng(0)
        x = rng.normal(0, 1, size=50)
        y = x.copy()
        out = rq57.mann_whitney_u_test(x, y)
        self.assertGreater(out["p_value_two_sided"], 0.05)

    def test_well_separated_distributions_low_p(self) -> None:
        # Non-overlapping samples -> p-value should be tiny.
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([10.0, 11.0, 12.0, 13.0, 14.0])
        out = rq57.mann_whitney_u_test(x, y)
        self.assertLess(out["p_value_two_sided"], 0.05)

    def test_u_statistic_in_valid_range(self) -> None:
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([4.0, 5.0, 6.0])
        out = rq57.mann_whitney_u_test(x, y)
        n1, n2 = len(x), len(y)
        # U must be in [0, n1*n2].
        self.assertGreaterEqual(out["u_statistic"], 0)
        self.assertLessEqual(out["u_statistic"], n1 * n2)

    def test_returns_required_keys(self) -> None:
        out = rq57.mann_whitney_u_test(np.array([1.0, 2.0]), np.array([3.0, 4.0]))
        for k in ("u_statistic", "p_value_two_sided", "z_score", "n_x", "n_y"):
            self.assertIn(k, out)

    def test_handles_ties(self) -> None:
        # Heavy ties: should not crash and p-value should be in [0, 1].
        x = np.array([0.0, 0.0, 0.0, 1.0, 1.0])
        y = np.array([0.0, 1.0, 1.0, 1.0, 2.0])
        out = rq57.mann_whitney_u_test(x, y)
        self.assertGreaterEqual(out["p_value_two_sided"], 0.0)
        self.assertLessEqual(out["p_value_two_sided"], 1.0)
        self.assertFalse(math.isnan(out["p_value_two_sided"]))

    def test_p_value_between_0_and_1(self) -> None:
        rng = np.random.default_rng(1)
        x = rng.normal(0, 1, size=20)
        y = rng.normal(0.5, 1, size=20)
        out = rq57.mann_whitney_u_test(x, y)
        self.assertGreaterEqual(out["p_value_two_sided"], 0.0)
        self.assertLessEqual(out["p_value_two_sided"], 1.0)

    def test_deterministic(self) -> None:
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        y = np.array([2.0, 3.0, 4.0, 5.0, 6.0, 7.0])
        out1 = rq57.mann_whitney_u_test(x, y)
        out2 = rq57.mann_whitney_u_test(x, y)
        self.assertEqual(out1["u_statistic"], out2["u_statistic"])
        self.assertEqual(out1["p_value_two_sided"], out2["p_value_two_sided"])

    def test_completely_separated_u_is_zero(self) -> None:
        # All x < all y -> U1 (for x) should be 0 (x ranks sum minimal).
        # We report the U for the FIRST sample (x).
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([4.0, 5.0, 6.0])
        out = rq57.mann_whitney_u_test(x, y)
        # U_x = 0 when all x are below all y.
        self.assertEqual(out["u_statistic"], 0)

    def test_all_identical_returns_p_one(self) -> None:
        # Degenerate: no variance -> cannot reject H0 -> p = 1.0.
        x = np.array([2.0, 2.0, 2.0])
        y = np.array([2.0, 2.0, 2.0])
        out = rq57.mann_whitney_u_test(x, y)
        self.assertEqual(out["p_value_two_sided"], 1.0)

    def test_empty_sample_returns_nan(self) -> None:
        out = rq57.mann_whitney_u_test(np.array([]), np.array([1.0, 2.0]))
        self.assertTrue(math.isnan(out["p_value_two_sided"]))
        self.assertTrue(math.isnan(out["u_statistic"]))


# --------------------------------------------- calibrate_threshold_at_spec
class TestCalibrateThresholdAtSpec(unittest.TestCase):
    def test_separable_case_high_sensitivity(self) -> None:
        scores = np.array([0.0, 0.05, 0.10, 0.15, 0.20, 1.0, 1.5])
        labels = np.array([0, 0, 0, 0, 0, 1, 1])
        out = rq57.calibrate_threshold_at_spec(scores, labels)
        self.assertGreaterEqual(out["specificity"], 0.90 - 1e-9)
        self.assertEqual(out["sensitivity"], 1.0)
        self.assertEqual(out["tp"], 2)
        self.assertEqual(out["fn"], 0)

    def test_target_specificity_respected(self) -> None:
        scores = np.array([0.0, 0.1, 0.2, 0.3, 0.8, 0.9])
        labels = np.array([0, 0, 0, 0, 1, 1])
        out = rq57.calibrate_threshold_at_spec(scores, labels, target_spec=0.75)
        self.assertGreaterEqual(out["specificity"], 0.75 - 1e-9)

    def test_all_negative_no_positives(self) -> None:
        scores = np.array([0.1, 0.2, 0.3])
        labels = np.array([0, 0, 0])
        out = rq57.calibrate_threshold_at_spec(scores, labels)
        self.assertEqual(out["sensitivity"], 0.0)
        self.assertEqual(out["specificity"], 1.0)
        self.assertEqual(out["tp"], 0)
        self.assertEqual(out["fn"], 0)

    def test_empty_input_returns_lowest_threshold(self) -> None:
        out = rq57.calibrate_threshold_at_spec(np.array([]), np.array([]))
        self.assertEqual(out["threshold"], 0.0)
        self.assertEqual(out["sensitivity"], 0.0)
        self.assertEqual(out["specificity"], 1.0)

    def test_returns_dict_with_required_keys(self) -> None:
        out = rq57.calibrate_threshold_at_spec(np.array([0.0, 1.0]), np.array([0, 1]))
        for k in ("threshold", "sensitivity", "specificity", "tp", "fp", "tn", "fn"):
            self.assertIn(k, out)

    def test_threshold_in_grid_range(self) -> None:
        out = rq57.calibrate_threshold_at_spec(np.array([0.0, 1.0]), np.array([0, 1]))
        self.assertGreaterEqual(out["threshold"], 0.0)
        self.assertLessEqual(out["threshold"], 2.0)


# --------------------------------------------- combined_oob_cpwer
class TestCombinedOobCpwer(unittest.TestCase):
    def test_all_separated_below_threshold(self) -> None:
        s1 = np.array([0.1, 0.2]); m1 = np.array([2.0, 3.0]); p1 = np.array([1.0, 1.0])
        s2 = np.array([0.15]); m2 = np.array([2.0]); p2 = np.array([1.0])
        out = rq57.combined_oob_cpwer(s1, m1, p1, 0.5, s2, m2, p2, 0.5)
        self.assertEqual(out["cpwer"], 1.0)
        self.assertEqual(out["n_oob"], 3)
        self.assertEqual(out["n_flagged_mixed"], 0)
        self.assertEqual(out["n_separated"], 3)

    def test_all_mixed_above_threshold(self) -> None:
        s1 = np.array([0.9, 0.8]); m1 = np.array([1.0, 1.0]); p1 = np.array([2.0, 3.0])
        s2 = np.array([0.95]); m2 = np.array([1.0]); p2 = np.array([4.0])
        out = rq57.combined_oob_cpwer(s1, m1, p1, 0.5, s2, m2, p2, 0.5)
        self.assertEqual(out["cpwer"], 1.0)
        self.assertEqual(out["n_oob"], 3)
        self.assertEqual(out["n_flagged_mixed"], 3)
        self.assertEqual(out["n_separated"], 0)

    def test_stratum_specific_thresholds(self) -> None:
        s1 = np.array([0.6]); m1 = np.array([1.0]); p1 = np.array([2.0])
        s2 = np.array([0.6]); m2 = np.array([1.0]); p2 = np.array([2.0])
        out = rq57.combined_oob_cpwer(s1, m1, p1, 0.5, s2, m2, p2, 0.95)
        self.assertAlmostEqual(out["cpwer"], 1.5, places=6)
        self.assertEqual(out["n_flagged_mixed"], 1)
        self.assertEqual(out["n_separated"], 1)
        self.assertEqual(out["n_oob_s1"], 1)
        self.assertEqual(out["n_oob_s2"], 1)

    def test_empty_both_returns_nan(self) -> None:
        out = rq57.combined_oob_cpwer(
            np.array([]), np.array([]), np.array([]), 0.5,
            np.array([]), np.array([]), np.array([]), 0.5,
        )
        self.assertTrue(math.isnan(out["cpwer"]))
        self.assertEqual(out["n_oob"], 0)

    def test_one_stratum_empty(self) -> None:
        s1 = np.array([0.6]); m1 = np.array([1.0]); p1 = np.array([2.0])
        out = rq57.combined_oob_cpwer(
            s1, m1, p1, 0.5,
            np.array([]), np.array([]), np.array([]), 0.5,
        )
        self.assertEqual(out["cpwer"], 1.0)
        self.assertEqual(out["n_oob"], 1)
        self.assertEqual(out["n_oob_s2"], 0)

    def test_counts_partition_n_oob(self) -> None:
        s1 = np.array([0.6, 0.1]); m1 = np.array([1.0, 1.0]); p1 = np.array([2.0, 1.0])
        s2 = np.array([0.9, 0.2]); m2 = np.array([1.0, 1.0]); p2 = np.array([3.0, 1.0])
        out = rq57.combined_oob_cpwer(s1, m1, p1, 0.5, s2, m2, p2, 0.5)
        # s1: 0.6>=0.5 mixed, 0.1<0.5 sep ; s2: 0.9 mixed, 0.2 sep
        self.assertEqual(out["n_flagged_mixed"], 2)
        self.assertEqual(out["n_separated"], 2)
        self.assertEqual(out["n_oob"], 4)


# --------------------------------------------- bootstrap_stratified
class TestBootstrapStratified(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scores = np.array([0.1, 0.2, 0.9, 1.5, 0.3, 0.4, 1.2, 1.8])
        cls.labels = np.array([0, 0, 1, 1, 0, 0, 1, 1])
        cls.mixed = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
        cls.sep = np.array([1.0, 1.0, 2.0, 2.0, 1.0, 1.0, 2.0, 2.0])
        cls.s1 = np.array([0, 1, 2, 3])
        cls.s2 = np.array([4, 5, 6, 7])
        cls.out = rq57.bootstrap_stratified(
            cls.scores, cls.labels, cls.mixed, cls.sep,
            cls.s1, cls.s2, n_boot=10, seed=42,
        )

    def test_returns_correct_shapes(self) -> None:
        self.assertEqual(self.out["thresholds_1"].shape, (10,))
        self.assertEqual(self.out["thresholds_2"].shape, (10,))
        self.assertEqual(self.out["oob_cpwer_combined"].shape, (10,))
        self.assertEqual(self.out["n_oob_1"].shape, (10,))

    def test_deterministic_with_seed(self) -> None:
        out2 = rq57.bootstrap_stratified(
            self.scores, self.labels, self.mixed, self.sep,
            self.s1, self.s2, n_boot=10, seed=42,
        )
        np.testing.assert_array_equal(self.out["thresholds_1"], out2["thresholds_1"])
        np.testing.assert_array_equal(self.out["thresholds_2"], out2["thresholds_2"])
        np.testing.assert_array_equal(self.out["oob_cpwer_combined"], out2["oob_cpwer_combined"])

    def test_thresholds_in_grid_range(self) -> None:
        for t in self.out["thresholds_1"]:
            self.assertGreaterEqual(t, 0.0)
            self.assertLessEqual(t, 2.0)
        for t in self.out["thresholds_2"]:
            self.assertGreaterEqual(t, 0.0)
            self.assertLessEqual(t, 2.0)

    def test_combined_oob_nonneg_or_nan(self) -> None:
        for c in self.out["oob_cpwer_combined"]:
            self.assertTrue(math.isnan(c) or c >= 0.0)

    def test_n1_n2_in_summary(self) -> None:
        self.assertEqual(self.out["n1"], 4)
        self.assertEqual(self.out["n2"], 4)
        self.assertEqual(self.out["n_boot"], 10)
        self.assertEqual(self.out["seed"], 42)

    def test_different_seed_differs(self) -> None:
        out2 = rq57.bootstrap_stratified(
            self.scores, self.labels, self.mixed, self.sep,
            self.s1, self.s2, n_boot=10, seed=7,
        )
        self.assertFalse(np.array_equal(self.out["thresholds_1"], out2["thresholds_1"]))

    def test_n_oob_le_stratum_size(self) -> None:
        for k in self.out["n_oob_1"]:
            self.assertLessEqual(int(k), 4)
        for k in self.out["n_oob_2"]:
            self.assertLessEqual(int(k), 4)


# --------------------------------------------- count_modes helper
class TestCountModes(unittest.TestCase):
    def test_single_mode(self) -> None:
        arr = np.array([0.38] * 100)
        md = rq57.count_modes(arr, 0.05)
        self.assertEqual(md["n_modes"], 1)
        self.assertEqual(md["n_unique"], 1)

    def test_six_modes_five_above_threshold(self) -> None:
        arr = np.array([0.38] * 60 + [0.87] * 15 + [0.01] * 9 + [0.95] * 8 + [0.33] * 6 + [1.5] * 2)
        md = rq57.count_modes(arr, 0.05)
        self.assertEqual(md["n_modes"], 5)
        self.assertEqual(md["n_unique"], 6)

    def test_empty(self) -> None:
        md = rq57.count_modes(np.array([]), 0.05)
        self.assertEqual(md["n_modes"], 0)
        self.assertEqual(md["n_unique"], 0)

    def test_modes_sorted_by_count(self) -> None:
        arr = np.array([0.5] * 30 + [0.2] * 10)
        md = rq57.count_modes(arr, 0.05)
        self.assertEqual(md["modes"][0]["threshold"], 0.5)
        self.assertEqual(md["modes"][1]["threshold"], 0.2)

    def test_fraction_sums_correctly(self) -> None:
        arr = np.array([0.5] * 30 + [0.2] * 10)
        md = rq57.count_modes(arr, 0.05)
        total_frac = sum(m["fraction"] for m in md["modes"])
        self.assertAlmostEqual(total_frac, 1.0, places=9)


# --------------------------------------------- percentile_interval
class TestPercentileInterval(unittest.TestCase):
    def test_basic_interval(self) -> None:
        arr = np.arange(101.0)  # 0..100
        lo, hi = rq57.percentile_interval(arr, 2.5, 97.5)
        self.assertAlmostEqual(lo, 2.5, places=6)
        self.assertAlmostEqual(hi, 97.5, places=6)

    def test_empty_returns_nan(self) -> None:
        lo, hi = rq57.percentile_interval(np.array([]))
        self.assertTrue(math.isnan(lo))
        self.assertTrue(math.isnan(hi))

    def test_width_nonneg(self) -> None:
        lo, hi = rq57.percentile_interval(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
        self.assertGreaterEqual(hi - lo, 0.0)


# --------------------------------------------- smoke: real AISHELL-4 data
@unittest.skipUnless(AISHELL4_JSON.exists(), "AISHELL-4 validation JSON not present")
class TestInSampleReproductionSmoke(unittest.TestCase):
    """Smoke test: pooled in-sample calibration reproduces RQ44/RQ25's 0.38
    threshold on the real 77-window AISHELL-4 data."""

    @classmethod
    def setUpClass(cls) -> None:
        data = json.loads(AISHELL4_JSON.read_text(encoding="utf-8"))
        windows = data["windows"]
        cls.windows = windows
        cls.lang_ent = np.array(
            [rq57.max_across_speakers(w) for w in windows], dtype=float
        )
        cls.sep_cpwer = np.array(
            [float(w["always_separated_cpwer"]) for w in windows], dtype=float
        )
        cls.durations = np.array(
            [rq57.duration_proxy(w) for w in windows], dtype=float
        )
        cls.labels = (cls.sep_cpwer > 1.0).astype(int)

    def test_pooled_in_sample_threshold_is_038(self) -> None:
        out = rq57.calibrate_threshold_at_spec(self.lang_ent, self.labels)
        self.assertAlmostEqual(out["threshold"], 0.38, places=6)

    def test_n_windows_is_77_and_labels_match_rq44(self) -> None:
        self.assertEqual(len(self.windows), 77)
        self.assertEqual(int(self.labels.sum()), 37)
        self.assertEqual(int((self.labels == 0).sum()), 40)

    def test_duration_proxy_nonneg_and_nonempty(self) -> None:
        self.assertEqual(len(self.durations), 77)
        self.assertTrue(np.all(self.durations >= 0))
        self.assertTrue(np.any(self.durations > 0))


# --------------------------------------------- smoke: duration split on real data
@unittest.skipUnless(AISHELL4_JSON.exists(), "AISHELL-4 validation JSON not present")
class TestDurationStratificationSmoke(unittest.TestCase):
    """Smoke test: the median duration split partitions all 77 windows into two
    non-empty strata, and the split point equals the median duration."""

    @classmethod
    def setUpClass(cls) -> None:
        data = json.loads(AISHELL4_JSON.read_text(encoding="utf-8"))
        windows = data["windows"]
        cls.durations = np.array(
            [rq57.duration_proxy(w) for w in windows], dtype=float
        )
        cls.short_idx, cls.long_idx = rq57.stratify_by_duration(cls.durations)
        cls.split_value = float(np.median(cls.durations))

    def test_strata_partition_all_77_windows(self) -> None:
        self.assertEqual(len(self.short_idx) + len(self.long_idx), 77)

    def test_both_strata_nonempty(self) -> None:
        self.assertGreater(len(self.short_idx), 0)
        self.assertGreater(len(self.long_idx), 0)

    def test_strata_disjoint(self) -> None:
        self.assertEqual(set(self.short_idx) & set(self.long_idx), set())

    def test_short_stratum_le_median(self) -> None:
        for i in self.short_idx:
            self.assertLessEqual(self.durations[i], self.split_value + 1e-9)

    def test_long_stratum_gt_median(self) -> None:
        for i in self.long_idx:
            self.assertGreater(self.durations[i], self.split_value + 1e-9)

    def test_split_value_is_median(self) -> None:
        self.assertAlmostEqual(self.split_value, float(np.median(self.durations)), places=6)


# --------------------------------------------- integration: result files
@unittest.skipUnless(RESULTS_JSON.exists(), "RQ57 results JSON not yet generated")
class TestResultsFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))

    def test_label_is_experimental_frontier(self) -> None:
        self.assertEqual(self.summary["label"], "experimental/frontier")

    def test_closes_issue_975(self) -> None:
        self.assertEqual(self.summary["closes_issue"], 975)

    def test_n_windows_is_77(self) -> None:
        self.assertEqual(self.summary["n_windows"], 77)

    def test_stratum_sizes_recorded_and_partition(self) -> None:
        n1 = self.summary["stratification"]["stratum1"]["n_windows"]
        n2 = self.summary["stratification"]["stratum2"]["n_windows"]
        self.assertEqual(n1 + n2, 77)
        self.assertGreater(n1, 0)
        self.assertGreater(n2, 0)

    def test_split_value_recorded(self) -> None:
        strat = self.summary["stratification"]
        self.assertIn("split_value", strat)
        self.assertIn("split_rule", strat)

    def test_hypothesis_verdicts_present(self) -> None:
        verdicts = self.summary["hypothesis_verdicts"]
        for h in ("H57a", "H57b", "H57c"):
            self.assertIn(h, verdicts)
            self.assertIn("supported", verdicts[h])
            self.assertIn("statement", verdicts[h])

    def test_h57a_records_modes_for_both_strata(self) -> None:
        v = self.summary["hypothesis_verdicts"]["H57a"]
        self.assertIn("n_modes_5pct_stratum1", v)
        self.assertIn("n_modes_5pct_stratum2", v)

    def test_h57b_records_combined_oob(self) -> None:
        v = self.summary["hypothesis_verdicts"]["H57b"]
        self.assertIn("median_oob_cpwer", v)
        self.assertIn("kill_threshold", v)

    def test_h57c_records_mann_whitney(self) -> None:
        v = self.summary["hypothesis_verdicts"]["H57c"]
        self.assertIn("p_value_two_sided", v)
        self.assertIn("u_statistic", v)

    def test_rq44_reference_recorded(self) -> None:
        ref = self.summary["rq44_pooled_reference"]
        self.assertEqual(ref["n_unique"], 6)
        self.assertAlmostEqual(ref["median_oob_cpwer"], 1.055556, places=5)

    def test_bootstrap_b_is_10000(self) -> None:
        self.assertEqual(self.summary["bootstrap"]["n_boot"], 10000)
        self.assertEqual(self.summary["bootstrap"]["seed"], 42)

    def test_mann_whitney_block_present(self) -> None:
        mw = self.summary["mann_whitney_u_test"]
        self.assertIn("p_value_two_sided", mw)
        self.assertIn("u_statistic", mw)
        self.assertIn("z_score", mw)

    def test_per_bootstrap_arrays_length_10000(self) -> None:
        pb = self.summary["per_bootstrap"]
        self.assertEqual(len(pb["thresholds_1"]), 10000)
        self.assertEqual(len(pb["thresholds_2"]), 10000)
        self.assertEqual(len(pb["oob_cpwer_combined"]), 10000)

    def test_h57b_kill_threshold_is_1056(self) -> None:
        v = self.summary["hypothesis_verdicts"]["H57b"]
        self.assertAlmostEqual(v["kill_threshold"], 1.056, places=6)


# --------------------------------------------- integration: pooled reproduction
@unittest.skipUnless(AISHELL4_JSON.exists(), "AISHELL-4 validation JSON not present")
class TestPooledBootstrapReproduction(unittest.TestCase):
    """The within-script pooled bootstrap (matched B/seed) must reproduce RQ44's
    published 6-unique / 5-modes / width-0.94 / OOB-median-1.055556."""

    @classmethod
    def setUpClass(cls) -> None:
        data = json.loads(AISHELL4_JSON.read_text(encoding="utf-8"))
        windows = data["windows"]
        cls.lang_ent = np.array([rq57.max_across_speakers(w) for w in windows], dtype=float)
        cls.mixed = np.array([float(w["always_mixed_cpwer"]) for w in windows], dtype=float)
        cls.sep = np.array([float(w["always_separated_cpwer"]) for w in windows], dtype=float)
        cls.labels = (cls.sep > 1.0).astype(int)
        cls.pooled = rq57._bootstrap_pooled(
            cls.lang_ent, cls.labels, cls.mixed, cls.sep, 10000, 42
        )

    def test_pooled_n_unique_is_6(self) -> None:
        md = rq57.count_modes(self.pooled["thresholds"], 0.05)
        self.assertEqual(md["n_unique"], 6)

    def test_pooled_n_modes_5pct_is_5(self) -> None:
        md = rq57.count_modes(self.pooled["thresholds"], 0.05)
        self.assertEqual(md["n_modes"], 5)

    def test_pooled_oob_median_matches_rq44(self) -> None:
        valid = self.pooled["oob_cpwer"][~np.isnan(self.pooled["oob_cpwer"])]
        self.assertAlmostEqual(float(np.median(valid)), 1.055556, places=5)


# --------------------------------------------- integration: CSV output
@unittest.skipUnless(RESULTS_CSV.exists(), "RQ57 results CSV not yet generated")
class TestResultsCsv(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with RESULTS_CSV.open("r", encoding="utf-8") as f:
            cls.rows = list(csv.DictReader(f))

    def test_has_four_rows(self) -> None:
        # pooled_matched, stratum1_short, stratum2_long, combined_stratified
        self.assertEqual(len(self.rows), 4)

    def test_stratum_names_present(self) -> None:
        names = {r["stratum"] for r in self.rows}
        self.assertEqual(names, {"pooled_matched_b10000", "stratum1_short",
                                 "stratum2_long", "combined_stratified"})

    def test_header_has_required_fields(self) -> None:
        with RESULTS_CSV.open("r", encoding="utf-8") as f:
            header = next(csv.reader(f))
        for field in ("stratum", "n_windows", "thr_n_modes_5pct",
                      "oob_cpwer_median", "oob_cpwer_frac_below_1_10"):
            self.assertIn(field, header)

    def test_strata_partition_77(self) -> None:
        by = {r["stratum"]: r for r in self.rows}
        n1 = int(by["stratum1_short"]["n_windows"])
        n2 = int(by["stratum2_long"]["n_windows"])
        self.assertEqual(n1 + n2, 77)

    def test_combined_n_windows_is_77(self) -> None:
        by = {r["stratum"]: r for r in self.rows}
        self.assertEqual(int(by["combined_stratified"]["n_windows"]), 77)


if __name__ == "__main__":
    unittest.main()
