"""Tests for RQ33: metadata-only Mode S detector (experimental/frontier).

Pins the pure helpers: compression ratio (Whisper-faithful), script category,
language-id entropy, per-speaker lengths, Shannon entropy of lengths, the 10
metadata features, two-sided threshold calibration, flag_at, ceiling analysis,
permutation test (deterministic with seed), numpy-only logistic regression
(sigmoid numerical stability, standardisation with constant columns, fit /
predict / LOO-CV, threshold calibration), and bootstrap CIs. The full driver
``main()`` is exercised via a smoke test on the real AISHELL-4 source JSON.

No Whisper / no audio needed — features are extracted from injected window
dicts (mirroring the structure of
``results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json``).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

# The RQ33 analysis script lives in results/frontier/ as a standalone module
# (no src. package). Import it via sys.path manipulation, mirroring the
# harness entropy_guard test pattern.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_DIR = _PROJECT_ROOT / "results" / "frontier" / "metadata_mode_s_detector"
sys.path.insert(0, str(_SCRIPT_DIR))

import metadata_detector_analysis as md  # noqa: E402  (path-injected import)


# ----------------------------------------------------------------- CR primitive
class TestCompressionRatio(unittest.TestCase):
    def test_empty_is_zero(self) -> None:
        self.assertEqual(md.compression_ratio(""), 0.0)

    def test_whitespace_only_is_zero(self) -> None:
        self.assertEqual(md.compression_ratio("   \n\t  "), 0.0)

    def test_repetitive_text_has_high_ratio(self) -> None:
        repetitive = "小小小小小小小小小小小小"
        normal = "今天天气真好我们去公园散步吧"
        self.assertGreater(md.compression_ratio(repetitive),
                           md.compression_ratio(normal))

    def test_returns_positive_for_normal_text(self) -> None:
        # CR is len(raw bytes) / len(compressed bytes); for short text the zlib
        # overhead can dominate and CR can be < 1.0. We only assert > 0.
        self.assertGreater(md.compression_ratio("hello world"), 0.0)


# -------------------------------------------------------------- script detection
class TestScriptCategory(unittest.TestCase):
    def test_space_is_space(self) -> None:
        self.assertEqual(md.script_category(" "), "Space")

    def test_han(self) -> None:
        self.assertEqual(md.script_category("你"), "Han")

    def test_latin(self) -> None:
        self.assertEqual(md.script_category("A"), "Latin")

    def test_digit(self) -> None:
        self.assertEqual(md.script_category("3"), "Digit")

    def test_punct(self) -> None:
        self.assertEqual(md.script_category(","), "Punct")


class TestLanguageIdEntropy(unittest.TestCase):
    def test_empty_is_zero(self) -> None:
        self.assertEqual(md.language_id_entropy(""), 0.0)

    def test_monoscript_chinese_is_zero(self) -> None:
        # Pure Han has zero entropy (one script category dominates)
        self.assertEqual(md.language_id_entropy("你好世界"), 0.0)

    def test_mixed_script_has_positive_entropy(self) -> None:
        # Half Han, half Latin => entropy near 1.0 bit
        ent = md.language_id_entropy("你好AB")
        self.assertGreater(ent, 0.5)
        self.assertLess(ent, 1.5)

    def test_balanced_three_scripts_higher_entropy(self) -> None:
        # Three equally-weighted categories => entropy = log2(3) ~ 1.585
        ent = md.language_id_entropy("你好A")  # Han Han Latin => 2/3 vs 1/3
        expected = -(2 / 3) * np.log2(2 / 3) - (1 / 3) * np.log2(1 / 3)
        self.assertAlmostEqual(ent, expected, places=6)


# ---------------------------------------------------------- per-speaker lengths
class TestPerSpeakerLengths(unittest.TestCase):
    def test_lengths_strip_whitespace(self) -> None:
        w = {"separated_text_per_speaker": {"s0": "  hello  ", "s1": "world\t"}}
        self.assertEqual(md.per_speaker_lengths(w), [5, 5])

    def test_empty_speakers_count_as_zero(self) -> None:
        w = {"separated_text_per_speaker": {"s0": "hello", "s1": "  ", "s2": ""}}
        self.assertEqual(md.per_speaker_lengths(w), [5, 0, 0])

    def test_missing_speakers_returns_empty(self) -> None:
        self.assertEqual(md.per_speaker_lengths({}), [])


class TestShannonEntropy(unittest.TestCase):
    def test_all_zero_returns_zero(self) -> None:
        self.assertEqual(md._shannon_entropy([0, 0, 0]), 0.0)

    def test_single_speaker_returns_zero(self) -> None:
        # All weight on one speaker => entropy 0
        self.assertEqual(md._shannon_entropy([100, 0, 0]), 0.0)

    def test_balanced_two_speakers_is_one_bit(self) -> None:
        self.assertAlmostEqual(md._shannon_entropy([50, 50]), 1.0, places=6)

    def test_balanced_three_speakers_is_log2_3(self) -> None:
        self.assertAlmostEqual(md._shannon_entropy([10, 10, 10]),
                               np.log2(3), places=6)


# -------------------------------------------------------- metadata feature extraction
class TestExtractMetadataFeatures(unittest.TestCase):
    def _window(self) -> dict:
        # Two speakers, one empty; separated text longer than mixed.
        return {
            "separated_runtime_sec": 4.6,
            "mixed_runtime_sec": 0.65,
            "separated_total_length": 98,
            "mixed_text_length": 96,
            "num_speakers": 2,
            "separated_text_per_speaker": {"s0": "x" * 98, "s1": ""},
        }

    def test_returns_all_10_features(self) -> None:
        feats = md.extract_metadata_features(self._window())
        self.assertEqual(set(feats.keys()), set(md.METADATA_FEATURES))

    def test_runtime_ratio_recomputed_from_raw_counts(self) -> None:
        feats = md.extract_metadata_features(self._window())
        # sep_runtime / mix_runtime = 4.6 / 0.65
        self.assertAlmostEqual(feats["runtime_ratio"], 4.6 / 0.65, places=6)

    def test_char_ratio_recomputed_from_raw_counts(self) -> None:
        feats = md.extract_metadata_features(self._window())
        self.assertAlmostEqual(feats["char_ratio"], 98.0 / 96.0, places=6)

    def test_num_speakers_is_int_as_float(self) -> None:
        feats = md.extract_metadata_features(self._window())
        self.assertEqual(feats["num_speakers"], 2.0)

    def test_num_active_speakers_excludes_empty(self) -> None:
        feats = md.extract_metadata_features(self._window())
        self.assertEqual(feats["num_active_speakers_sep"], 1.0)

    def test_avg_speaker_length_excludes_empty(self) -> None:
        feats = md.extract_metadata_features(self._window())
        # Only one non-empty speaker with 98 chars => mean = 98
        self.assertAlmostEqual(feats["avg_speaker_length_sep"], 98.0, places=6)

    def test_length_entropy_for_dominant_speaker(self) -> None:
        # One speaker carries everything => entropy = 0
        feats = md.extract_metadata_features(self._window())
        self.assertAlmostEqual(feats["length_entropy_speakers"], 0.0, places=6)

    def test_safe_div_handles_zero_mix_runtime(self) -> None:
        w = self._window()
        w["mixed_runtime_sec"] = 0.0
        feats = md.extract_metadata_features(w)
        # _safe_div returns 0.0 when denominator < EPS
        self.assertEqual(feats["runtime_ratio"], 0.0)


class TestMetadataFeaturesContract(unittest.TestCase):
    def test_exactly_10_features(self) -> None:
        self.assertEqual(len(md.METADATA_FEATURES), 10)

    def test_feature_order_stable(self) -> None:
        # The LR consumes features positionally; the order must be locked.
        expected = (
            "sep_runtime_sec", "mix_runtime_sec", "runtime_ratio",
            "sep_total_chars", "mix_total_chars", "char_ratio",
            "num_speakers", "num_active_speakers_sep",
            "avg_speaker_length_sep", "length_entropy_speakers",
        )
        self.assertEqual(md.METADATA_FEATURES, expected)


# ------------------------------------------------------- threshold calibration
class TestCalibrateTwoSided(unittest.TestCase):
    def test_high_direction_picks_max_sens_ms_at_target_spec(self) -> None:
        # 10 negs in [0, 1, 2, ..., 9], Mode S at [10, 11], all-halluc at [10, 11, 12].
        # Threshold 10 in "high" direction: spec = 1.0 (no negs >= 10), sens_MS = 1.0.
        neg = [float(i) for i in range(10)]
        pos_ms = [10.0, 11.0]
        pos_ah = [10.0, 11.0, 12.0]
        op = md.calibrate_two_sided(neg, pos_ms, pos_ah, target_spec=0.90)
        self.assertEqual(op["direction"], "high")
        self.assertGreaterEqual(op["specificity"], 0.90)
        self.assertEqual(op["sensitivity_mode_s"], 1.0)
        self.assertEqual(op["tp_mode_s"], 2)

    def test_low_direction_can_be_chosen_when_better(self) -> None:
        # Mode S sits at the low end (0, 1); negs in [5..14]; so "low" catches both.
        neg = [float(i) for i in range(5, 15)]
        pos_ms = [0.0, 1.0]
        pos_ah = [0.0, 1.0, 12.0]
        op = md.calibrate_two_sided(neg, pos_ms, pos_ah, target_spec=0.90)
        self.assertEqual(op["direction"], "low")
        self.assertGreaterEqual(op["specificity"], 0.90)
        self.assertEqual(op["sensitivity_mode_s"], 1.0)

    def test_no_threshold_meets_spec_returns_none_direction(self) -> None:
        # Mode S sits at 5 inside the neg range [0..9]. The "high" direction's
        # max-neg threshold (t=9) has spec=0.9 (1 neg >= 9) which is below the
        # 0.95 target; "low" direction's min-neg threshold (t=0) has spec=0.9
        # (1 neg <= 0). With target_spec=0.95 NO candidate threshold meets the
        # spec in either direction, so the function returns direction="none".
        neg = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
        pos_ms = [5.0, 5.0]
        pos_ah = [5.0, 5.0]
        op = md.calibrate_two_sided(neg, pos_ms, pos_ah, target_spec=0.95)
        self.assertEqual(op["direction"], "none")
        self.assertEqual(op["sensitivity_mode_s"], 0.0)


class TestFlagAt(unittest.TestCase):
    def test_high_direction(self) -> None:
        self.assertTrue(md.flag_at(1.5, "high", 1.0))
        self.assertTrue(md.flag_at(1.0, "high", 1.0))  # boundary inclusive
        self.assertFalse(md.flag_at(0.9, "high", 1.0))

    def test_low_direction(self) -> None:
        self.assertTrue(md.flag_at(0.5, "low", 1.0))
        self.assertTrue(md.flag_at(1.0, "low", 1.0))  # boundary inclusive
        self.assertFalse(md.flag_at(1.5, "low", 1.0))

    def test_none_direction_never_flags(self) -> None:
        self.assertFalse(md.flag_at(99.0, "none", 0.0))


class TestCeilingAnalysis(unittest.TestCase):
    def test_returns_one_entry_per_spec_floor(self) -> None:
        neg = [float(i) for i in range(10)]
        pos_ms = [10.0, 11.0]
        floors = [0.5, 0.7, 0.9]
        out = md.ceiling_analysis(neg, pos_ms, floors)
        self.assertEqual(len(out), 3)
        self.assertEqual([r["specificity_floor"] for r in out], floors)

    def test_relaxed_floor_can_catch_more(self) -> None:
        # Mode S at 8 sits just above the highest neg at 7; high direction at t=8
        # has spec=1.0 and sens_MS=0.5; lowering spec to 0.5 doesn't help here.
        neg = [float(i) for i in range(8)]  # 0..7
        pos_ms = [8.0, 9.0]
        out = md.ceiling_analysis(neg, pos_ms, [0.5, 0.9])
        # At both floors, threshold 8 in "high" direction reaches spec=1.0, sens=1.0
        self.assertGreaterEqual(out[0]["max_sensitivity_mode_s"], 0.99)
        self.assertGreaterEqual(out[1]["max_sensitivity_mode_s"], 0.99)


# --------------------------------------------------------------- permutation test
class TestPermutationTest(unittest.TestCase):
    def test_deterministic_with_seed(self) -> None:
        vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        mask = np.array([True, True, False, False, False, False, False, False, False, False])
        a = md.permutation_test(vals, mask, n_perm=200, seed=42)
        b = md.permutation_test(vals, mask, n_perm=200, seed=42)
        self.assertEqual(a["p_value_two_sided"], b["p_value_two_sided"])

    def test_different_seeds_can_differ(self) -> None:
        # With 1000 perms the p-value is usually stable across seeds, but the
        # test at least guarantees no crash and a valid p-value range.
        vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        mask = np.array([True, False, True, False, False, False])
        a = md.permutation_test(vals, mask, n_perm=100, seed=1)
        self.assertGreater(a["p_value_two_sided"], 0.0)
        self.assertLessEqual(a["p_value_two_sided"], 1.0)

    def test_extreme_difference_low_p_value(self) -> None:
        # 2 positives at the extreme high end vs 18 negatives at the low end.
        # The observed stat is very large; p-value should be small.
        vals = np.array(list(range(18)) + [100.0, 101.0], dtype=float)
        mask = np.array([False] * 18 + [True, True])
        out = md.permutation_test(vals, mask, n_perm=500, seed=42)
        self.assertLess(out["p_value_two_sided"], 0.1)

    def test_no_positives_safe(self) -> None:
        vals = np.array([1.0, 2.0, 3.0])
        mask = np.array([False, False, False])
        out = md.permutation_test(vals, mask, n_perm=50, seed=42)
        self.assertEqual(out["mode_s_mean"], 0.0)

    def test_plus_one_smoothing(self) -> None:
        # p-value = (n_extreme + 1) / (n_perm + 1), so always > 0.
        vals = np.array([1.0, 2.0, 3.0, 4.0])
        mask = np.array([True, False, False, False])
        out = md.permutation_test(vals, mask, n_perm=10, seed=42)
        self.assertGreater(out["p_value_two_sided"], 0.0)


# --------------------------------------------------- numpy-only logistic regression
class TestSigmoid(unittest.TestCase):
    def test_zero_is_half(self) -> None:
        self.assertAlmostEqual(float(md._sigmoid(np.array([0.0]))[0]), 0.5, places=9)

    def test_large_positive_does_not_overflow(self) -> None:
        out = md._sigmoid(np.array([1000.0]))
        self.assertEqual(float(out[0]), 1.0)

    def test_large_negative_does_not_underflow_to_nan(self) -> None:
        out = md._sigmoid(np.array([-1000.0]))
        self.assertTrue(np.isfinite(out[0]))
        self.assertLess(float(out[0]), 1e-9)

    def test_monotone(self) -> None:
        z = np.array([-3.0, -1.0, 0.0, 1.0, 3.0])
        s = md._sigmoid(z)
        self.assertTrue(np.all(np.diff(s) > 0))


class TestStandardize(unittest.TestCase):
    def test_constant_column_handled(self) -> None:
        # std==0 column should be left at 0 (mu=center, sd=1.0 guard).
        X = np.array([[1.0, 5.0], [2.0, 5.0], [3.0, 5.0]])
        mu, sd = md.standardize_fit(X)
        Xs = md.standardize_apply(X, mu, sd)
        # Constant column should be centered to zero with no division-by-zero.
        self.assertTrue(np.allclose(Xs[:, 1], 0.0))

    def test_zero_mean_unit_std_after_apply(self) -> None:
        X = np.array([[1.0], [2.0], [3.0], [4.0]])
        mu, sd = md.standardize_fit(X)
        Xs = md.standardize_apply(X, mu, sd)
        self.assertAlmostEqual(float(Xs.mean()), 0.0, places=9)
        self.assertAlmostEqual(float(Xs.std()), 1.0, places=9)


class TestFitLogisticRegression(unittest.TestCase):
    def test_separable_case_converges_with_strong_l2(self) -> None:
        # Two clusters well separated; with strong L2 the weights stay finite.
        X = np.array([[0.0], [0.1], [10.0], [10.1]])
        y = np.array([0.0, 0.0, 1.0, 1.0])
        w = md.fit_logistic_regression(X, y, l2=10.0, lr=0.1, n_iter=2000, seed=42)
        self.assertTrue(np.all(np.isfinite(w)))

    def test_class_balanced_weights_finite_with_one_positive(self) -> None:
        # 1 positive among 4 (mirrors LOO-fold structure with n_pos=1)
        X = np.array([[0.0], [0.1], [0.2], [10.0]])
        y = np.array([0.0, 0.0, 0.0, 1.0])
        # Strong L2 prevents the single positive from saturating
        w = md.fit_logistic_regression(X, y, l2=50.0, lr=0.05, n_iter=2000, seed=42)
        self.assertTrue(np.all(np.isfinite(w)))


class TestPredictProba(unittest.TestCase):
    def test_outputs_in_unit_interval(self) -> None:
        X = np.array([[0.0], [1.0], [2.0], [3.0]])
        y = np.array([0.0, 0.0, 1.0, 1.0])
        mu, sd = md.standardize_fit(X)
        w = md.fit_logistic_regression(X, y, l2=1.0, lr=0.1, n_iter=2000, seed=42)
        p = md.predict_proba(X, w, mu, sd)
        self.assertTrue(np.all((p >= 0.0) & (p <= 1.0)))

    def test_higher_feature_value_higher_proba_for_positive_slope(self) -> None:
        X = np.array([[0.0], [10.0]])
        y = np.array([0.0, 1.0])
        mu, sd = md.standardize_fit(X)
        w = md.fit_logistic_regression(X, y, l2=0.1, lr=0.5, n_iter=5000, seed=42)
        p = md.predict_proba(X, w, mu, sd)
        self.assertGreater(p[1], p[0])


class TestLooCvPredict(unittest.TestCase):
    def test_returns_n_predictions(self) -> None:
        X = np.array([[float(i)] for i in range(10)])
        y = np.array([0.0] * 8 + [1.0, 1.0])
        oof = md.loo_cv_predict(X, y, l2=10.0, lr=0.1, n_iter=500, seed=42)
        self.assertEqual(len(oof), 10)

    def test_deterministic_with_seed(self) -> None:
        X = np.array([[float(i)] for i in range(10)])
        y = np.array([0.0] * 8 + [1.0, 1.0])
        a = md.loo_cv_predict(X, y, l2=10.0, lr=0.1, n_iter=500, seed=42)
        b = md.loo_cv_predict(X, y, l2=10.0, lr=0.1, n_iter=500, seed=42)
        np.testing.assert_allclose(a, b)

    def test_oof_in_unit_interval(self) -> None:
        X = np.array([[float(i)] for i in range(10)])
        y = np.array([0.0] * 8 + [1.0, 1.0])
        oof = md.loo_cv_predict(X, y, l2=10.0, lr=0.1, n_iter=500, seed=42)
        self.assertTrue(np.all((oof >= 0.0) & (oof <= 1.0)))


class TestCalibrateProbabilityThreshold(unittest.TestCase):
    def test_one_sided_high_only(self) -> None:
        # negs in [0.0, 0.1, 0.2]; pos_ms in [0.9, 1.0]; threshold in "high" dir.
        neg = np.array([0.0, 0.1, 0.2])
        pos_ms = np.array([0.9, 1.0])
        op = md.calibrate_probability_threshold(neg, pos_ms, target_spec=0.90)
        self.assertEqual(op["direction"], "high")
        self.assertGreaterEqual(op["specificity"], 0.90)
        self.assertEqual(op["sensitivity_mode_s"], 1.0)

    def test_no_threshold_meets_spec_returns_default(self) -> None:
        # negs and positives fully overlap; can't reach 90% spec with sens > 0.
        neg = np.array([0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3])
        pos_ms = np.array([0.5, 0.6])
        op = md.calibrate_probability_threshold(neg, pos_ms, target_spec=0.90)
        self.assertEqual(op["sensitivity_mode_s"], 0.0)


# --------------------------------------------------------------------- bootstrap
class TestBootstrapSensitivityCI(unittest.TestCase):
    def test_ci_bounds_valid(self) -> None:
        scores = np.array([0.9, 0.95, 0.1, 0.2, 0.3])
        labels = np.array([1.0, 1.0, 0.0, 0.0, 0.0])
        lo, hi = md.bootstrap_sensitivity_ci(
            scores, labels, direction="high", threshold=0.5, n_boot=200, seed=42)
        self.assertLessEqual(lo, hi)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)

    def test_perfect_classifier_ci_near_one(self) -> None:
        scores = np.array([0.99, 0.99, 0.01, 0.01])
        labels = np.array([1.0, 1.0, 0.0, 0.0])
        lo, hi = md.bootstrap_sensitivity_ci(
            scores, labels, direction="high", threshold=0.5, n_boot=500, seed=42)
        self.assertGreaterEqual(lo, 0.99)

    def test_deterministic_with_seed(self) -> None:
        scores = np.array([0.9, 0.1, 0.2, 0.8])
        labels = np.array([1.0, 0.0, 0.0, 1.0])
        a = md.bootstrap_sensitivity_ci(scores, labels, "high", 0.5, n_boot=200, seed=42)
        b = md.bootstrap_sensitivity_ci(scores, labels, "high", 0.5, n_boot=200, seed=42)
        self.assertEqual(a, b)


class TestBootstrapSpecificityCI(unittest.TestCase):
    def test_ci_bounds_valid(self) -> None:
        scores = np.array([0.9, 0.95, 0.1, 0.2, 0.3])
        labels = np.array([1.0, 1.0, 0.0, 0.0, 0.0])
        lo, hi = md.bootstrap_specificity_ci(
            scores, labels, direction="high", threshold=0.5, n_boot=200, seed=42)
        self.assertLessEqual(lo, hi)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)


# ------------------------------------------------------------------ main driver
class TestMainDriver(unittest.TestCase):
    """Smoke test: main() must run end-to-end on the real AISHELL-4 source JSON
    and produce both output files with the expected schema.

    The full driver is expensive (LOO-CV over 77 windows for 9 L2 values plus
    1000-perm permutation tests for 10 features plus 10000-resample bootstraps),
    so it runs exactly ONCE in setUpClass and the test methods assert on the
    resulting files.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.src_json = (
            _PROJECT_ROOT
            / "results"
            / "external_sanity_check"
            / "aishell4"
            / "rq1_aishell4_validation_results.json"
        )
        if not cls.src_json.exists():
            raise unittest.SkipTest(f"AISHELL-4 source JSON missing: {cls.src_json}")
        # Run the full driver once. Subsequent tests read the produced files.
        md.main()

    def test_main_writes_csv_and_json(self) -> None:
        self.assertTrue(md.OUT_CSV.exists(), f"CSV missing: {md.OUT_CSV}")
        self.assertTrue(md.OUT_JSON.exists(), f"JSON missing: {md.OUT_JSON}")

    def test_json_summary_schema(self) -> None:
        summary = json.loads(md.OUT_JSON.read_text(encoding="utf-8"))
        for key in ("label", "rq", "closes_issue", "n_windows",
                    "n_hallucinated_tracks", "n_nonhallucinated_tracks",
                    "n_mode_s_tracks", "mode_s_window_ids", "metadata_features",
                    "per_feature_detectors", "combined_metadata_lr",
                    "ensemble_metadata_or_lang_id", "hypothesis_verdicts"):
            self.assertIn(key, summary, f"missing top-level key: {key}")

    def test_label_is_experimental_frontier(self) -> None:
        summary = json.loads(md.OUT_JSON.read_text(encoding="utf-8"))
        self.assertEqual(summary["label"], "experimental/frontier")

    def test_closes_issue_940(self) -> None:
        summary = json.loads(md.OUT_JSON.read_text(encoding="utf-8"))
        self.assertEqual(summary["closes_issue"], 940)

    def test_mode_s_is_exactly_windows_22_and_30(self) -> None:
        summary = json.loads(md.OUT_JSON.read_text(encoding="utf-8"))
        self.assertEqual(sorted(summary["mode_s_window_ids"]), [22, 30])
        self.assertEqual(summary["n_mode_s_tracks"], 2)

    def test_10_metadata_features_present(self) -> None:
        summary = json.loads(md.OUT_JSON.read_text(encoding="utf-8"))
        self.assertEqual(len(summary["metadata_features"]), 10)
        self.assertEqual(set(summary["metadata_features"]), set(md.METADATA_FEATURES))

    def test_hypothesis_verdicts_present(self) -> None:
        summary = json.loads(md.OUT_JSON.read_text(encoding="utf-8"))
        verdicts = summary["hypothesis_verdicts"]
        for h in ("H33a", "H33b", "H33c"):
            self.assertIn(h, verdicts)
            self.assertIn("supported", verdicts[h])
            self.assertIn("reason", verdicts[h])

    def test_per_window_rows_have_lr_columns(self) -> None:
        summary = json.loads(md.OUT_JSON.read_text(encoding="utf-8"))
        rows = summary["per_window"]
        self.assertGreater(len(rows), 0)
        for r in rows:
            self.assertIn("metadata_lr_prob", r)
            self.assertIn("metadata_lr_flag", r)
            self.assertIn("ensemble_flag", r)

    def test_csv_has_expected_columns(self) -> None:
        first_line = md.OUT_CSV.read_text(encoding="utf-8").splitlines()[0]
        header = first_line.split(",")
        for col in ("window_id", "hallucinated", "mode_s", "metadata_lr_prob",
                    "metadata_lr_flag", "ensemble_flag"):
            self.assertIn(col, header)
        # all 10 metadata features in the CSV
        for feat in md.METADATA_FEATURES:
            self.assertIn(feat, header)


if __name__ == "__main__":
    unittest.main()
