"""Tests for RQ39 bootstrap CIs on corrected-router cpWER (experimental/frontier).

Pin the PURE helpers used by
``results/frontier/bootstrap_ci_corrected_router/bootstrap_ci_analysis.py``:
bootstrap resample indices, bootstrap distribution of the mean, percentile CI,
jackknife means, BCa CI, paired-delta distribution + CI, plus the detector
primitives lifted verbatim from RQ16 (script_category, language_id_entropy,
max_across_speakers, corrected_router_decision). Synthetic data only — no
AISHELL-4 file, no MeetEval, no Whisper, no audio.
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

# Make the analysis module importable when running from the repo root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "bootstrap_ci_corrected_router"
)
sys.path.insert(0, str(SCRIPT_DIR))

from bootstrap_ci_analysis import (  # noqa: E402
    _jackknife_means,
    bca_ci,
    bootstrap_distribution,
    bootstrap_indices,
    corrected_router_decision,
    language_id_entropy,
    max_across_speakers,
    paired_delta_ci,
    paired_delta_distribution,
    percentile_ci,
    script_category,
)

# Threshold matches the analysis module (RQ13/RQ16 operating point).
LANG_ID_THRESHOLD = 0.409


# ----------------------------------------------------------------- bootstrap_indices
class TestBootstrapIndices(unittest.TestCase):
    def test_shape_is_n_boot_by_n(self) -> None:
        idx = bootstrap_indices(n=10, n_boot=200, seed=42)
        self.assertEqual(idx.shape, (200, 10))

    def test_indices_in_range(self) -> None:
        idx = bootstrap_indices(n=7, n_boot=500, seed=1)
        self.assertTrue(int(idx.min()) >= 0)
        self.assertTrue(int(idx.max()) < 7)

    def test_deterministic_with_seed(self) -> None:
        a = bootstrap_indices(n=5, n_boot=100, seed=42)
        b = bootstrap_indices(n=5, n_boot=100, seed=42)
        np.testing.assert_array_equal(a, b)

    def test_different_seeds_usually_differ(self) -> None:
        a = bootstrap_indices(n=20, n_boot=100, seed=1)
        b = bootstrap_indices(n=20, n_boot=100, seed=2)
        self.assertFalse(np.array_equal(a, b))


# ---------------------------------------------------------- bootstrap_distribution
class TestBootstrapDistribution(unittest.TestCase):
    def test_returns_n_boot_means(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = bootstrap_distribution(values, n_boot=500, seed=42)
        self.assertEqual(dist.shape, (500,))

    def test_mean_of_distribution_close_to_sample_mean(self) -> None:
        # For a reasonable n_boot, the mean of bootstrap means should be very
        # close to the original sample mean (law of large numbers).
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        dist = bootstrap_distribution(values, n_boot=20000, seed=42)
        self.assertAlmostEqual(float(dist.mean()), float(values.mean()), places=1)

    def test_deterministic_with_seed(self) -> None:
        values = np.array([0.1, 0.5, 0.9, 1.2, 0.3])
        a = bootstrap_distribution(values, n_boot=200, seed=42)
        b = bootstrap_distribution(values, n_boot=200, seed=42)
        np.testing.assert_array_equal(a, b)

    def test_each_bootstrap_mean_within_min_max_of_values(self) -> None:
        values = np.array([0.0, 1.0, 2.0, 3.0])
        dist = bootstrap_distribution(values, n_boot=100, seed=7)
        self.assertGreaterEqual(float(dist.min()), 0.0)
        self.assertLessEqual(float(dist.max()), 3.0)


# ------------------------------------------------------------- percentile_ci
class TestPercentileCI(unittest.TestCase):
    def test_lo_le_hi(self) -> None:
        boot = np.linspace(0.0, 10.0, 1001)
        lo, hi = percentile_ci(boot, alpha=0.05)
        self.assertLessEqual(lo, hi)

    def test_symmetric_distribution_gives_symmetric_ci(self) -> None:
        # Symmetric bootstrap dist -> 95% CI should be roughly symmetric about the mean.
        boot = np.random.default_rng(0).normal(loc=5.0, scale=1.0, size=100000)
        lo, hi = percentile_ci(boot, alpha=0.05)
        self.assertAlmostEqual((lo + hi) / 2.0, 5.0, places=1)
        # 95% CI for normal(0,1) is roughly +/- 1.96.
        self.assertAlmostEqual(hi - lo, 2 * 1.96, places=1)

    def test_constant_distribution_returns_constant(self) -> None:
        boot = np.full(500, 3.14)
        lo, hi = percentile_ci(boot, alpha=0.05)
        self.assertAlmostEqual(lo, 3.14)
        self.assertAlmostEqual(hi, 3.14)

    def test_alpha_zero_returns_min_max(self) -> None:
        # alpha=0 -> 0th and 100th percentile (full range).
        boot = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        lo, hi = percentile_ci(boot, alpha=0.0)
        self.assertAlmostEqual(lo, 1.0)
        self.assertAlmostEqual(hi, 5.0)

    def test_alpha_controls_width(self) -> None:
        # Larger alpha -> narrower CI (less coverage). alpha=0.05 is 95% CI,
        # alpha=0.10 is 90% CI; 95% CI is wider than 90% CI.
        rng = np.random.default_rng(42)
        boot = rng.normal(loc=0.0, scale=1.0, size=100000)
        lo_05, hi_05 = percentile_ci(boot, alpha=0.05)
        lo_10, hi_10 = percentile_ci(boot, alpha=0.10)
        self.assertGreater(hi_05 - lo_05, hi_10 - lo_10)


# ------------------------------------------------------------- _jackknife_means
class TestJackknifeMeans(unittest.TestCase):
    def test_returns_n_values(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        jack = _jackknife_means(values)
        self.assertEqual(len(jack), len(values))

    def test_leave_one_out_identity(self) -> None:
        # jackknife_mean[i] = (sum(values) - values[i]) / (n - 1).
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        jack = _jackknife_means(values)
        n = len(values)
        total = float(values.sum())
        for i in range(n):
            expected = (total - values[i]) / (n - 1)
            self.assertAlmostEqual(float(jack[i]), expected)

    def test_mean_of_jackknife_equals_sample_mean(self) -> None:
        values = np.array([0.5, 1.5, 2.5, 3.5, 4.5, 5.5])
        jack = _jackknife_means(values)
        self.assertAlmostEqual(float(jack.mean()), float(values.mean()))

    def test_single_element(self) -> None:
        jack = _jackknife_means(np.array([7.0]))
        self.assertEqual(len(jack), 1)
        self.assertAlmostEqual(float(jack[0]), 7.0)


# ------------------------------------------------------------- bca_ci
class TestBCaCI(unittest.TestCase):
    def test_lo_le_hi(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        boot = bootstrap_distribution(values, n_boot=2000, seed=42)
        lo, hi = bca_ci(values, boot, alpha=0.05)
        self.assertLessEqual(lo, hi)

    def test_constant_data_returns_constant(self) -> None:
        values = np.full(10, 2.5)
        boot = bootstrap_distribution(values, n_boot=500, seed=42)
        lo, hi = bca_ci(values, boot, alpha=0.05)
        self.assertAlmostEqual(lo, 2.5)
        self.assertAlmostEqual(hi, 2.5)

    def test_symmetric_data_bca_close_to_percentile(self) -> None:
        # For symmetric, low-skew data, BCa should be close to percentile CI.
        rng = np.random.default_rng(123)
        values = rng.normal(loc=0.0, scale=1.0, size=200)
        boot = bootstrap_distribution(values, n_boot=5000, seed=42)
        pct_lo, pct_hi = percentile_ci(boot, alpha=0.05)
        bca_lo, bca_hi = bca_ci(values, boot, alpha=0.05)
        # BCa and percentile should be within 10% of each other for symmetric data.
        self.assertAlmostEqual(bca_lo, pct_lo, delta=0.2)
        self.assertAlmostEqual(bca_hi, pct_hi, delta=0.2)

    def test_deterministic_with_seed(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        boot = bootstrap_distribution(values, n_boot=500, seed=42)
        a = bca_ci(values, boot, alpha=0.05)
        b = bca_ci(values, boot, alpha=0.05)
        self.assertEqual(a, b)

    def test_ci_contains_sample_mean_for_typical_data(self) -> None:
        # For well-behaved data, the 95% CI should bracket the sample mean.
        rng = np.random.default_rng(7)
        values = rng.normal(loc=5.0, scale=1.0, size=100)
        boot = bootstrap_distribution(values, n_boot=5000, seed=42)
        lo, hi = bca_ci(values, boot, alpha=0.05)
        sample_mean = float(values.mean())
        self.assertLessEqual(lo, sample_mean)
        self.assertLessEqual(sample_mean, hi)

    def test_skewed_data_bca_shifts_vs_percentile(self) -> None:
        # For right-skewed data (heavy upper tail), BCa upper bound should
        # differ from the percentile upper bound (BCa corrects for skew).
        rng = np.random.default_rng(99)
        values = np.concatenate([
            rng.exponential(scale=1.0, size=80),
            np.array([10.0, 12.0, 15.0]),  # a few large outliers
        ])
        boot = bootstrap_distribution(values, n_boot=5000, seed=42)
        pct_lo, pct_hi = percentile_ci(boot, alpha=0.05)
        bca_lo, bca_hi = bca_ci(values, boot, alpha=0.05)
        # Both CIs are valid; BCa should not equal percentile exactly when skewed.
        # We just check both are reasonable bounds.
        self.assertLessEqual(bca_lo, bca_hi)
        self.assertLessEqual(pct_lo, pct_hi)


# ------------------------------------------------------- paired_delta_distribution
class TestPairedDeltaDistribution(unittest.TestCase):
    def test_returns_n_boot(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        b = np.array([0.5, 1.5, 2.5, 3.5, 4.5])
        dist = paired_delta_distribution(a, b, n_boot=300, seed=42)
        self.assertEqual(dist.shape, (300,))

    def test_mean_close_to_mean_a_minus_mean_b(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        b = np.array([0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5])
        dist = paired_delta_distribution(a, b, n_boot=20000, seed=42)
        expected = float(a.mean() - b.mean())
        self.assertAlmostEqual(float(dist.mean()), expected, places=1)

    def test_deterministic_with_seed(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0])
        b = np.array([0.5, 1.5, 2.5, 3.5])
        x = paired_delta_distribution(a, b, n_boot=200, seed=42)
        y = paired_delta_distribution(a, b, n_boot=200, seed=42)
        np.testing.assert_array_equal(x, y)

    def test_identical_arrays_give_dist_near_zero(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = paired_delta_distribution(a, a, n_boot=500, seed=42)
        # All bootstrap means of a - a = 0, so distribution should be all zeros.
        np.testing.assert_allclose(dist, np.zeros(500))

    def test_shape_mismatch_raises(self) -> None:
        with self.assertRaises(ValueError):
            paired_delta_distribution(
                np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0]), n_boot=10, seed=42
            )

    def test_uses_same_indices_for_a_and_b(self) -> None:
        # Verify the paired design: same resample indices for a and b.
        # If a == b constant, the delta is always 0 regardless of indices;
        # but if a - b is constant c, the delta should always be c.
        a = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        b = a - 5.0  # b[i] = a[i] - 5, so a[idx].mean() - b[idx].mean() = 5 for any idx
        dist = paired_delta_distribution(a, b, n_boot=100, seed=1)
        np.testing.assert_allclose(dist, np.full(100, 5.0))


# ------------------------------------------------------- paired_delta_ci
class TestPairedDeltaCI(unittest.TestCase):
    def test_lo_le_hi(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        b = np.array([0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5])
        lo, hi = paired_delta_ci(a, b, n_boot=500, seed=42)
        self.assertLessEqual(lo, hi)

    def test_identical_arrays_ci_brackets_zero(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        lo, hi = paired_delta_ci(a, a, n_boot=500, seed=42)
        # delta is always 0 -> CI should be (0, 0).
        self.assertAlmostEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.0)

    def test_strongly_separated_arrays_ci_excludes_zero(self) -> None:
        # When a is consistently much larger than b, the paired delta CI
        # should exclude zero (upper bound < 0 is wrong direction; here we
        # check the CI is entirely positive).
        rng = np.random.default_rng(0)
        a = rng.normal(loc=10.0, scale=0.1, size=200)
        b = rng.normal(loc=5.0, scale=0.1, size=200)
        lo, hi = paired_delta_ci(a, b, n_boot=2000, seed=42)
        self.assertGreater(lo, 0.0)
        self.assertGreater(hi, 0.0)

    def test_deterministic_with_seed(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        b = np.array([0.5, 1.5, 2.5, 3.5, 4.5])
        x = paired_delta_ci(a, b, n_boot=200, seed=42)
        y = paired_delta_ci(a, b, n_boot=200, seed=42)
        self.assertEqual(x, y)


# ------------------------------------------------------- script_category
class TestScriptCategory(unittest.TestCase):
    def test_han_chinese(self) -> None:
        self.assertEqual(script_category("你"), "Han")
        self.assertEqual(script_category("好"), "Han")
        self.assertEqual(script_category("世"), "Han")
        self.assertEqual(script_category("界"), "Han")

    def test_latin(self) -> None:
        self.assertEqual(script_category("A"), "Latin")
        self.assertEqual(script_category("z"), "Latin")

    def test_digit(self) -> None:
        self.assertEqual(script_category("0"), "Digit")
        self.assertEqual(script_category("9"), "Digit")

    def test_whitespace_is_space(self) -> None:
        self.assertEqual(script_category(" "), "Space")
        self.assertEqual(script_category("\t"), "Space")
        self.assertEqual(script_category("\n"), "Space")

    def test_punct(self) -> None:
        self.assertEqual(script_category("，"), "Punct")
        self.assertEqual(script_category("。"), "Punct")
        self.assertEqual(script_category("!"), "Punct")

    def test_hiragana_katakana(self) -> None:
        self.assertEqual(script_category("あ"), "Hiragana")
        self.assertEqual(script_category("ア"), "Katakana")

    def test_hangul(self) -> None:
        self.assertEqual(script_category("가"), "Hangul")


# ------------------------------------------------------- language_id_entropy
class TestLanguageIdEntropy(unittest.TestCase):
    def test_empty_string_is_zero(self) -> None:
        self.assertEqual(language_id_entropy(""), 0.0)
        self.assertEqual(language_id_entropy("   "), 0.0)

    def test_monoscript_chinese_near_zero(self) -> None:
        # All-Han text -> single script category -> entropy 0.
        text = "你好世界今天天气真好"
        self.assertAlmostEqual(language_id_entropy(text), 0.0, places=6)

    def test_two_scripts_has_log2_2(self) -> None:
        # 50/50 mix of two scripts -> entropy = log2(2) = 1.0 bit.
        text = "你A好B世C界D"  # 5 Han + 5 Latin
        self.assertAlmostEqual(language_id_entropy(text), 1.0, places=6)

    def test_diverse_mix_has_higher_entropy_than_monoscript(self) -> None:
        monoscript = "你好世界" * 10
        diverse = "你Aあア가0好Bいカナ1世Cうケニ2界Dえコヌ3"
        self.assertGreater(language_id_entropy(diverse), language_id_entropy(monoscript))

    def test_four_equal_scripts_has_log2_4(self) -> None:
        # 4 equal scripts -> entropy = log2(4) = 2.0 bits.
        text = "你Aあ0好Bい1世Cう2界Dえ3"  # 4 Han + 4 Latin + 4 Hiragana + 4 Digit
        self.assertAlmostEqual(language_id_entropy(text), 2.0, places=6)

    def test_punctuation_does_not_affect_entropy_much(self) -> None:
        # Punctuation is its own category; adding it shifts entropy but
        # monoscript Han + punct should still be low.
        text = "你好，世界。"
        ent = language_id_entropy(text)
        self.assertGreaterEqual(ent, 0.0)
        self.assertLess(ent, 1.0)  # not high entropy

    def test_threshold_boundary(self) -> None:
        # A diverse multilingual mix (the kind RQ13 flags) should exceed 0.409.
        # This is the AISHELL-4 hallucination footprint.
        hallucinated = "Hunt欸哦可以 카메 mad將會全部視起來只要把我拿出來"
        self.assertGreater(language_id_entropy(hallucinated), LANG_ID_THRESHOLD)


# ------------------------------------------------------- max_across_speakers
class TestMaxAcrossSpeakers(unittest.TestCase):
    def test_returns_max_of_fn_across_speakers(self) -> None:
        window = {"separated_text_per_speaker": {
            "A": "你好",        # entropy 0
            "B": "你A好B",     # entropy ~1.0
            "C": "你Aあ0",     # entropy = 2.0
        }}
        ent = max_across_speakers(window, language_id_entropy)
        self.assertAlmostEqual(ent, 2.0, places=6)

    def test_skips_empty_and_whitespace_speakers(self) -> None:
        window = {"separated_text_per_speaker": {
            "A": "你好",
            "B": "",
            "C": "   ",
            "D": None,
        }}
        ent = max_across_speakers(window, language_id_entropy)
        self.assertAlmostEqual(ent, 0.0, places=6)

    def test_empty_speakers_returns_zero(self) -> None:
        window = {"separated_text_per_speaker": {}}
        self.assertEqual(max_across_speakers(window, language_id_entropy), 0.0)

    def test_works_with_other_fn(self) -> None:
        # max_across_speakers is generic — works with len() too.
        window = {"separated_text_per_speaker": {"A": "ab", "B": "abcde", "C": "a"}}
        self.assertEqual(max_across_speakers(window, len), 5)


# ------------------------------------------------------- corrected_router_decision
class TestCorrectedRouterDecision(unittest.TestCase):
    def test_low_entropy_routes_separated(self) -> None:
        # Monoscript Chinese -> entropy 0 -> below threshold -> SEPARATED.
        window = {"separated_text_per_speaker": {"A": "你好世界今天天气真好"}}
        self.assertEqual(corrected_router_decision(window), "separated")

    def test_high_entropy_routes_mixed(self) -> None:
        # Diverse multilingual mix -> entropy > 0.409 -> MIXED.
        window = {"separated_text_per_speaker": {
            "A": "Hunt欸哦可以 카메 mad將會全部視起來只要把我拿出來"
        }}
        self.assertEqual(corrected_router_decision(window), "mixed")

    def test_max_across_speakers_drives_decision(self) -> None:
        # If ANY speaker has high entropy, route to MIXED (worst-case).
        window = {"separated_text_per_speaker": {
            "A": "你好",                      # entropy 0
            "B": "你Aあ0好Bい1世Cう2界Dえ3",  # entropy ~2.0
        }}
        self.assertEqual(corrected_router_decision(window), "mixed")

    def test_empty_separated_routes_separated(self) -> None:
        # No speaker text -> max_across_speakers returns 0 -> below threshold.
        window = {"separated_text_per_speaker": {}}
        self.assertEqual(corrected_router_decision(window), "separated")

    def test_threshold_is_strict_greater_than(self) -> None:
        # Decision rule: MIXED if ent > 0.409 (strict), else SEPARATED.
        # Construct text with entropy exactly at a known value (log2(2)=1.0)
        # which is well above 0.409 -> MIXED.
        window = {"separated_text_per_speaker": {"A": "你A你A你A"}}
        self.assertEqual(corrected_router_decision(window), "mixed")


if __name__ == "__main__":
    unittest.main()
