"""Tests for RQ64: retrospective bootstrap power analysis (experimental/frontier).

Pin the PURE helpers used by
``results/frontier/bootstrap_power_analysis/bootstrap_power_analysis.py``:
detector primitives (script_category, language_id_entropy, max_across_speakers,
corrected_router_decision), bootstrap helpers lifted from RQ39 (bootstrap_indices,
bootstrap_distribution, percentile_ci, _jackknife_means, bca_ci), and the NEW
RQ64 extrapolated-bootstrap helpers (extrapolated_bootstrap_distribution,
extrapolated_bca_at_n, find_min_n_to_exclude, compute_effect_size,
ci_includes_value).

The integration test runs the full analysis and asserts the output JSON is
well-formed, the n=77 BCa CI reproduces RQ39 bit-for-bit (H64a), and the
hypothesis verdicts are internally consistent. No MeetEval is required (RQ64
uses stored word-level cpWER only). Synthetic data for the pure helpers — no
AISHELL-4 file, no Whisper, no audio, no LLM.
"""
from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path

import numpy as np

# Load the analysis module from the results/frontier path (it is a standalone
# script, not under src/).
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = (
    _PROJECT_ROOT
    / "results"
    / "frontier"
    / "bootstrap_power_analysis"
    / "bootstrap_power_analysis.py"
)
_spec = importlib.util.spec_from_file_location(
    "bootstrap_power_analysis", _MODULE_PATH
)
assert _spec is not None and _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


# =================================================================== script_category
class ScriptCategoryTest(unittest.TestCase):
    """RQ13 detector primitive — must classify Unicode scripts correctly."""

    def test_chinese_character_is_han(self) -> None:
        self.assertEqual(mod.script_category("商"), "Han")
        self.assertEqual(mod.script_category("场"), "Han")

    def test_latin_character_is_latin(self) -> None:
        self.assertEqual(mod.script_category("A"), "Latin")
        self.assertEqual(mod.script_category("z"), "Latin")

    def test_digit_is_digit(self) -> None:
        self.assertEqual(mod.script_category("3"), "Digit")

    def test_whitespace_is_space(self) -> None:
        self.assertEqual(mod.script_category(" "), "Space")
        self.assertEqual(mod.script_category("\t"), "Space")

    def test_hangul_is_hangul(self) -> None:
        self.assertEqual(mod.script_category("카"), "Hangul")

    def test_katakana_is_katakana(self) -> None:
        self.assertEqual(mod.script_category("カ"), "Katakana")


# ============================================================ language_id_entropy
class LanguageIdEntropyTest(unittest.TestCase):
    """RQ13 lang-id entropy detector — clean Chinese ~ 0, diverse > threshold."""

    def test_clean_chinese_has_near_zero_entropy(self) -> None:
        ent = mod.language_id_entropy("零零幺商场经理这次把大家伙儿叫过来")
        self.assertLess(ent, 0.05)

    def test_diverse_multilingual_has_high_entropy(self) -> None:
        ent = mod.language_id_entropy("商 abc 카 メ")
        self.assertGreater(ent, mod.LANG_ID_ENTROPY_THRESHOLD)

    def test_empty_text_returns_zero(self) -> None:
        self.assertEqual(mod.language_id_entropy(""), 0.0)
        self.assertEqual(mod.language_id_entropy("   "), 0.0)

    def test_pure_single_script_has_near_zero_entropy(self) -> None:
        ent = mod.language_id_entropy("hello")
        self.assertLess(ent, 0.05)

    def test_threshold_is_0_38(self) -> None:
        self.assertEqual(mod.LANG_ID_ENTROPY_THRESHOLD, 0.38)


# ============================================================ max_across_speakers
class MaxAcrossSpeakersTest(unittest.TestCase):
    def test_returns_max_of_fn_over_speakers(self) -> None:
        window = {"separated_text_per_speaker": {"a": "商", "b": "abc"}}
        ent = mod.max_across_speakers(window, mod.language_id_entropy)
        self.assertLess(ent, 0.05)

    def test_returns_high_entropy_when_any_speaker_diverse(self) -> None:
        window = {"separated_text_per_speaker": {"a": "商", "b": "商 abc 카 メ"}}
        ent = mod.max_across_speakers(window, mod.language_id_entropy)
        self.assertGreater(ent, mod.LANG_ID_ENTROPY_THRESHOLD)

    def test_skips_empty_speakers(self) -> None:
        window = {"separated_text_per_speaker": {"a": "", "b": "   ", "c": "商"}}
        ent = mod.max_across_speakers(window, mod.language_id_entropy)
        self.assertLess(ent, 0.05)

    def test_returns_zero_when_all_speakers_empty(self) -> None:
        window = {"separated_text_per_speaker": {"a": "", "b": "  "}}
        self.assertEqual(
            mod.max_across_speakers(window, mod.language_id_entropy), 0.0
        )

    def test_missing_separated_text_returns_zero(self) -> None:
        window = {}
        self.assertEqual(
            mod.max_across_speakers(window, mod.language_id_entropy), 0.0
        )


# ====================================================== corrected_router_decision
class CorrectedRouterDecisionTest(unittest.TestCase):
    def test_low_entropy_routes_to_separated(self) -> None:
        window = {"separated_text_per_speaker": {"a": "零零幺商场经理"}}
        self.assertEqual(mod.corrected_router_decision(window), "separated")

    def test_high_entropy_routes_to_mixed(self) -> None:
        window = {"separated_text_per_speaker": {"a": "商 abc 卡 メ 12"}}
        self.assertEqual(mod.corrected_router_decision(window), "mixed")

    def test_threshold_0_38_is_used(self) -> None:
        window = {"separated_text_per_speaker": {"a": "商 abc カ メ"}}
        self.assertEqual(mod.corrected_router_decision(window), "mixed")

    def test_empty_window_routes_to_separated(self) -> None:
        window = {"separated_text_per_speaker": {"a": ""}}
        self.assertEqual(mod.corrected_router_decision(window), "separated")


# ============================================================ bootstrap_indices
class BootstrapIndicesTest(unittest.TestCase):
    def test_shape_is_n_boot_by_n(self) -> None:
        idx = mod.bootstrap_indices(n=10, n_boot=200, seed=42)
        self.assertEqual(idx.shape, (200, 10))

    def test_indices_in_range(self) -> None:
        idx = mod.bootstrap_indices(n=7, n_boot=500, seed=1)
        self.assertGreaterEqual(int(idx.min()), 0)
        self.assertLess(int(idx.max()), 7)

    def test_deterministic_with_seed(self) -> None:
        a = mod.bootstrap_indices(n=5, n_boot=100, seed=42)
        b = mod.bootstrap_indices(n=5, n_boot=100, seed=42)
        np.testing.assert_array_equal(a, b)

    def test_different_seeds_usually_differ(self) -> None:
        a = mod.bootstrap_indices(n=20, n_boot=100, seed=1)
        b = mod.bootstrap_indices(n=20, n_boot=100, seed=2)
        self.assertFalse(np.array_equal(a, b))


# ============================================================ bootstrap_distribution
class BootstrapDistributionTest(unittest.TestCase):
    def test_returns_n_boot_means(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = mod.bootstrap_distribution(values, n_boot=500, seed=42)
        self.assertEqual(dist.shape, (500,))

    def test_mean_of_distribution_close_to_sample_mean(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        dist = mod.bootstrap_distribution(values, n_boot=20000, seed=42)
        self.assertAlmostEqual(float(dist.mean()), float(values.mean()), places=1)

    def test_deterministic_with_seed(self) -> None:
        values = np.array([0.1, 0.5, 0.9, 1.2, 0.3])
        a = mod.bootstrap_distribution(values, n_boot=200, seed=42)
        b = mod.bootstrap_distribution(values, n_boot=200, seed=42)
        np.testing.assert_array_equal(a, b)

    def test_each_bootstrap_mean_within_min_max(self) -> None:
        values = np.array([0.0, 1.0, 2.0, 3.0])
        dist = mod.bootstrap_distribution(values, n_boot=100, seed=7)
        self.assertGreaterEqual(float(dist.min()), 0.0)
        self.assertLessEqual(float(dist.max()), 3.0)


# ============================================================ percentile_ci
class PercentileCITest(unittest.TestCase):
    def test_lo_le_hi(self) -> None:
        boot = np.linspace(0.0, 10.0, 1001)
        lo, hi = mod.percentile_ci(boot, alpha=0.05)
        self.assertLessEqual(lo, hi)

    def test_symmetric_distribution_gives_symmetric_ci(self) -> None:
        boot = np.random.default_rng(0).normal(loc=5.0, scale=1.0, size=100000)
        lo, hi = mod.percentile_ci(boot, alpha=0.05)
        self.assertAlmostEqual((lo + hi) / 2.0, 5.0, places=1)
        self.assertAlmostEqual(hi - lo, 2 * 1.96, places=1)

    def test_constant_distribution_returns_constant(self) -> None:
        boot = np.full(500, 3.14)
        lo, hi = mod.percentile_ci(boot, alpha=0.05)
        self.assertAlmostEqual(lo, 3.14)
        self.assertAlmostEqual(hi, 3.14)

    def test_alpha_zero_returns_min_max(self) -> None:
        boot = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        lo, hi = mod.percentile_ci(boot, alpha=0.0)
        self.assertAlmostEqual(lo, 1.0)
        self.assertAlmostEqual(hi, 5.0)


# ============================================================ _jackknife_means
class JackknifeMeansTest(unittest.TestCase):
    def test_length_matches_input(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0])
        jack = mod._jackknife_means(values)
        self.assertEqual(len(jack), 4)

    def test_jackknife_mean_formula(self) -> None:
        # Leave-one-out mean of [1,2,3,4] dropping 1 -> (2+3+4)/3 = 3.0
        values = np.array([1.0, 2.0, 3.0, 4.0])
        jack = mod._jackknife_means(values)
        self.assertAlmostEqual(jack[0], 3.0)
        self.assertAlmostEqual(jack[3], 2.0)

    def test_single_element_returns_array_of_one(self) -> None:
        jack = mod._jackknife_means(np.array([5.0]))
        self.assertEqual(len(jack), 1)
        self.assertAlmostEqual(float(jack[0]), 5.0)

    def test_mean_of_jackknife_equals_sample_mean(self) -> None:
        values = np.array([0.5, 1.5, 2.5, 3.5, 4.5])
        jack = mod._jackknife_means(values)
        self.assertAlmostEqual(float(jack.mean()), float(values.mean()), places=6)


# ============================================================ bca_ci
class BcaCITest(unittest.TestCase):
    def test_lo_le_hi(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        boot = mod.bootstrap_distribution(values, n_boot=2000, seed=42)
        lo, hi = mod.bca_ci(values, boot)
        self.assertLessEqual(lo, hi)

    def test_constant_data_returns_constant(self) -> None:
        values = np.full(10, 2.5)
        boot = mod.bootstrap_distribution(values, n_boot=500, seed=42)
        lo, hi = mod.bca_ci(values, boot)
        self.assertAlmostEqual(lo, 2.5)
        self.assertAlmostEqual(hi, 2.5)

    def test_ci_contains_sample_mean(self) -> None:
        values = np.array([0.1, 0.5, 0.9, 1.2, 0.3, 0.7, 1.1, 0.4])
        boot = mod.bootstrap_distribution(values, n_boot=5000, seed=42)
        lo, hi = mod.bca_ci(values, boot)
        self.assertLessEqual(lo, float(values.mean()))
        self.assertLessEqual(float(values.mean()), hi)

    def test_deterministic_with_seed(self) -> None:
        values = np.array([0.1, 0.5, 0.9, 1.2, 0.3, 0.7, 1.1, 0.4])
        boot1 = mod.bootstrap_distribution(values, n_boot=1000, seed=42)
        boot2 = mod.bootstrap_distribution(values, n_boot=1000, seed=42)
        lo1, hi1 = mod.bca_ci(values, boot1)
        lo2, hi2 = mod.bca_ci(values, boot2)
        self.assertAlmostEqual(lo1, lo2)
        self.assertAlmostEqual(hi1, hi2)

    def test_single_element_returns_itself(self) -> None:
        values = np.array([3.14])
        boot = mod.bootstrap_distribution(values, n_boot=100, seed=42)
        lo, hi = mod.bca_ci(values, boot)
        self.assertAlmostEqual(lo, 3.14)
        self.assertAlmostEqual(hi, 3.14)


# ============================================================ extrapolated_bootstrap_distribution  [NEW RQ64]
class ExtrapolatedBootstrapDistributionTest(unittest.TestCase):
    """The core RQ64 extrapolated bootstrap — must shrink as n grows and
    reproduce the standard bootstrap at n_target = len(population)."""

    def test_returns_n_boot_means(self) -> None:
        pop = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = mod.extrapolated_bootstrap_distribution(
            pop, n_target=10, n_boot=500, seed=42
        )
        self.assertEqual(dist.shape, (500,))

    def test_mean_close_to_population_mean(self) -> None:
        pop = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])
        dist = mod.extrapolated_bootstrap_distribution(
            pop, n_target=20, n_boot=20000, seed=42
        )
        self.assertAlmostEqual(float(dist.mean()), float(pop.mean()), places=1)

    def test_width_shrinks_as_n_grows(self) -> None:
        # CI width scales as 1/sqrt(n); larger n_target -> narrower bootstrap dist.
        pop = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])
        small = mod.extrapolated_bootstrap_distribution(
            pop, n_target=10, n_boot=5000, seed=42
        )
        large = mod.extrapolated_bootstrap_distribution(
            pop, n_target=1000, n_boot=5000, seed=42
        )
        self.assertLess(float(large.std()), float(small.std()))

    def test_deterministic_with_seed(self) -> None:
        pop = np.array([0.1, 0.5, 0.9, 1.2, 0.3])
        a = mod.extrapolated_bootstrap_distribution(
            pop, n_target=50, n_boot=200, seed=42
        )
        b = mod.extrapolated_bootstrap_distribution(
            pop, n_target=50, n_boot=200, seed=42
        )
        np.testing.assert_array_equal(a, b)

    def test_reproduces_standard_bootstrap_at_n_equal_population(self) -> None:
        # At n_target = len(population), the extrapolated bootstrap must equal
        # RQ39's bootstrap_distribution bit-for-bit (same RNG stream, chunked).
        # This is the H64a reproducibility guarantee.
        pop = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        extra = mod.extrapolated_bootstrap_distribution(
            pop, n_target=len(pop), n_boot=1000, seed=42, chunk=500
        )
        standard = mod.bootstrap_distribution(pop, n_boot=1000, seed=42)
        np.testing.assert_array_equal(extra, standard)

    def test_reproduces_standard_bootstrap_with_small_chunk(self) -> None:
        # Chunking does not change the RNG stream; chunk=1 must still match.
        pop = np.array([2.0, 3.0, 5.0, 7.0, 11.0])
        extra = mod.extrapolated_bootstrap_distribution(
            pop, n_target=len(pop), n_boot=300, seed=7, chunk=1
        )
        standard = mod.bootstrap_distribution(pop, n_boot=300, seed=7)
        np.testing.assert_array_equal(extra, standard)

    def test_indices_in_population_range(self) -> None:
        pop = np.array([10.0, 20.0, 30.0])
        dist = mod.extrapolated_bootstrap_distribution(
            pop, n_target=100, n_boot=500, seed=1
        )
        # Each bootstrap mean must lie within [min, max] of population.
        self.assertGreaterEqual(float(dist.min()), 10.0)
        self.assertLessEqual(float(dist.max()), 30.0)

    def test_n_target_below_one_raises(self) -> None:
        pop = np.array([1.0, 2.0, 3.0])
        with self.assertRaises(ValueError):
            mod.extrapolated_bootstrap_distribution(
                pop, n_target=0, n_boot=100, seed=42
            )

    def test_width_scales_as_inverse_sqrt_n(self) -> None:
        # The bootstrap std should scale ~ 1/sqrt(n). Doubling n should halve
        # the variance (i.e. std shrinks by ~sqrt(2)).
        pop = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])
        d1 = mod.extrapolated_bootstrap_distribution(
            pop, n_target=100, n_boot=8000, seed=42
        )
        d2 = mod.extrapolated_bootstrap_distribution(
            pop, n_target=400, n_boot=8000, seed=42
        )
        # d2 has 4x the n -> std should be ~ half of d1's std.
        ratio = float(d1.std()) / float(d2.std())
        self.assertAlmostEqual(ratio, 2.0, places=1)


# ============================================================ extrapolated_bca_at_n  [NEW RQ64]
class ExtrapolatedBcaAtNTest(unittest.TestCase):
    def test_returns_dict_with_required_keys(self) -> None:
        pop = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        res = mod.extrapolated_bca_at_n(pop, n_target=10, n_boot=500, seed=42)
        for k in ("n", "theta_hat", "boot_mean", "boot_std",
                  "pct_ci_lo", "pct_ci_hi", "bca_ci_lo", "bca_ci_hi",
                  "bca_width", "pct_width"):
            self.assertIn(k, res)

    def test_theta_hat_is_population_mean(self) -> None:
        pop = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        res = mod.extrapolated_bca_at_n(pop, n_target=20, n_boot=500, seed=42)
        self.assertAlmostEqual(res["theta_hat"], float(pop.mean()), places=6)

    def test_bca_lo_le_hi(self) -> None:
        pop = np.array([0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5])
        res = mod.extrapolated_bca_at_n(pop, n_target=30, n_boot=2000, seed=42)
        self.assertLessEqual(res["bca_ci_lo"], res["bca_ci_hi"])

    def test_bca_width_shrinks_as_n_grows(self) -> None:
        pop = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        small = mod.extrapolated_bca_at_n(pop, n_target=10, n_boot=3000, seed=42)
        large = mod.extrapolated_bca_at_n(pop, n_target=500, n_boot=3000, seed=42)
        self.assertLess(large["bca_width"], small["bca_width"])

    def test_deterministic_with_seed(self) -> None:
        pop = np.array([0.1, 0.5, 0.9, 1.2, 0.3, 0.7])
        a = mod.extrapolated_bca_at_n(pop, n_target=50, n_boot=1000, seed=42)
        b = mod.extrapolated_bca_at_n(pop, n_target=50, n_boot=1000, seed=42)
        self.assertAlmostEqual(a["bca_ci_lo"], b["bca_ci_lo"])
        self.assertAlmostEqual(a["bca_ci_hi"], b["bca_ci_hi"])

    def test_reproduces_rq39_bca_at_n_equal_population(self) -> None:
        # At n_target = len(population), the extrapolated BCa CI must equal
        # RQ39's bca_ci bit-for-bit. This is the H64a reproducibility check.
        pop = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        res = mod.extrapolated_bca_at_n(
            pop, n_target=len(pop), n_boot=2000, seed=42, chunk=500
        )
        boot = mod.bootstrap_distribution(pop, n_boot=2000, seed=42)
        lo, hi = mod.bca_ci(pop, boot)
        self.assertAlmostEqual(res["bca_ci_lo"], lo, places=9)
        self.assertAlmostEqual(res["bca_ci_hi"], hi, places=9)

    def test_bca_ci_concentrates_at_theta_hat_for_large_n(self) -> None:
        # As n -> infinity, BCa CI -> [theta_hat, theta_hat].
        pop = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        res = mod.extrapolated_bca_at_n(
            pop, n_target=5000, n_boot=3000, seed=42
        )
        # At n=5000 the CI should be very narrow around the mean 3.0.
        self.assertLess(res["bca_width"], 0.1)
        self.assertAlmostEqual(res["bca_ci_lo"], 3.0, places=1)
        self.assertAlmostEqual(res["bca_ci_hi"], 3.0, places=1)


# ============================================================ find_min_n_to_exclude  [NEW RQ64]
class FindMinNToExcludeTest(unittest.TestCase):
    def test_returns_min_n_when_ci_excludes(self) -> None:
        # Population mean = 3.0; oracle = 2.0. At small n the CI includes 2.0;
        # at large n the CI narrows and lower bound > 2.0.
        pop = np.array([2.5, 3.0, 3.5, 3.0, 3.0, 3.5, 2.5, 3.5])
        n_list = [8, 16, 32, 64, 128, 256]
        min_n = mod.find_min_n_to_exclude(
            pop, oracle=2.0, n_list=n_list, n_boot=2000, seed=42
        )
        self.assertIsNotNone(min_n)
        self.assertIn(min_n, n_list)

    def test_returns_none_when_never_excludes(self) -> None:
        # Population mean = 3.0; oracle = 3.0 (effect size 0). CI always
        # includes the oracle (the point estimate IS the oracle).
        pop = np.array([2.0, 3.0, 4.0, 3.0, 3.0])
        n_list = [5, 10, 20, 40]
        min_n = mod.find_min_n_to_exclude(
            pop, oracle=3.0, n_list=n_list, n_boot=2000, seed=42
        )
        self.assertIsNone(min_n)

    def test_returns_none_when_oracle_above_theta_hat(self) -> None:
        # Population mean = 2.0; oracle = 3.0 (oracle is BETTER / lower-better
        # inverted). The CI centers below oracle, so the upper bound may exceed
        # oracle but the lower bound never does -> never excludes via lower>oracle.
        pop = np.array([1.5, 2.0, 2.5, 2.0, 2.0])
        n_list = [5, 10, 20, 40]
        min_n = mod.find_min_n_to_exclude(
            pop, oracle=3.0, n_list=n_list, n_boot=2000, seed=42
        )
        self.assertIsNone(min_n)

    def test_returns_first_n_in_sorted_order(self) -> None:
        # Even if n_list is unsorted, the function should search ascending.
        pop = np.array([2.5, 3.0, 3.5, 3.0, 3.0, 3.5, 2.5, 3.5])
        n_list_unsorted = [256, 64, 8, 128, 32, 16]
        min_n = mod.find_min_n_to_exclude(
            pop, oracle=2.0, n_list=n_list_unsorted, n_boot=2000, seed=42
        )
        self.assertIsNotNone(min_n)
        # min_n must be the smallest n that excludes, regardless of input order.
        for n in sorted(n_list_unsorted):
            if n < min_n:
                # n below min_n should NOT exclude.
                res = mod.extrapolated_bca_at_n(
                    pop, n, n_boot=2000, seed=42
                )
                self.assertLessEqual(
                    res["bca_ci_lo"], 2.0,
                    f"n={n} below min_n={min_n} but already excludes"
                )

    def test_deterministic_with_seed(self) -> None:
        pop = np.array([2.5, 3.0, 3.5, 3.0, 3.0, 3.5, 2.5, 3.5])
        n_list = [8, 16, 32, 64]
        a = mod.find_min_n_to_exclude(
            pop, oracle=2.0, n_list=n_list, n_boot=2000, seed=42
        )
        b = mod.find_min_n_to_exclude(
            pop, oracle=2.0, n_list=n_list, n_boot=2000, seed=42
        )
        self.assertEqual(a, b)


# ============================================================ compute_effect_size  [NEW RQ64]
class ComputeEffectSizeTest(unittest.TestCase):
    def test_positive_when_corrected_above_oracle(self) -> None:
        self.assertAlmostEqual(mod.compute_effect_size(1.043, 1.017), 0.026, places=3)

    def test_zero_when_equal(self) -> None:
        self.assertAlmostEqual(mod.compute_effect_size(1.0, 1.0), 0.0)

    def test_negative_when_corrected_below_oracle(self) -> None:
        self.assertAlmostEqual(mod.compute_effect_size(0.9, 1.0), -0.1)


# ============================================================ ci_includes_value  [NEW RQ64]
class CiIncludesValueTest(unittest.TestCase):
    def test_value_inside_ci(self) -> None:
        self.assertTrue(mod.ci_includes_value((1.0, 2.0), 1.5))

    def test_value_at_lower_bound(self) -> None:
        self.assertTrue(mod.ci_includes_value((1.0, 2.0), 1.0))

    def test_value_at_upper_bound(self) -> None:
        self.assertTrue(mod.ci_includes_value((1.0, 2.0), 2.0))

    def test_value_below_ci(self) -> None:
        self.assertFalse(mod.ci_includes_value((1.0, 2.0), 0.5))

    def test_value_above_ci(self) -> None:
        self.assertFalse(mod.ci_includes_value((1.0, 2.0), 2.5))


# ============================================================ integration test
class IntegrationTest(unittest.TestCase):
    """Run the full analysis and assert the output JSON is well-formed and
    consistent with RQ39 (H64a baseline must reproduce RQ39's BCa CI)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.out_json = mod.OUT_JSON
        cls.out_csv = mod.OUT_CSV
        if not cls.out_json.exists():
            mod.main()
        cls.data = json.loads(cls.out_json.read_text(encoding="utf-8"))

    # --- label / source / structure
    def test_label_is_experimental_frontier(self) -> None:
        self.assertEqual(self.data["label"], "experimental/frontier")

    def test_closes_issue_988(self) -> None:
        self.assertEqual(self.data["closes_issue"], 988)

    def test_n_windows_is_77(self) -> None:
        self.assertEqual(self.data["n_windows"], 77)

    def test_threshold_is_0_38(self) -> None:
        self.assertAlmostEqual(
            self.data["thresholds"]["lang_id_entropy"], 0.38, places=6
        )

    def test_bootstrap_config(self) -> None:
        self.assertEqual(self.data["bootstrap"]["n_boot"], 10000)
        self.assertEqual(self.data["bootstrap"]["seed"], 42)
        self.assertEqual(self.data["bootstrap"]["alpha"], 0.05)

    def test_h64b_tractable_threshold_is_770(self) -> None:
        self.assertEqual(
            self.data["thresholds"]["h64b_tractable_threshold"], 770
        )

    def test_h64c_negligible_threshold_is_0_01(self) -> None:
        self.assertEqual(
            self.data["thresholds"]["h64c_negligible_threshold"], 0.01
        )

    # --- decision counts (sanity: must match RQ39/RQ55: mixed=38, separated=39)
    def test_lang_id_decision_counts_match_rq39(self) -> None:
        dc = self.data["decision_counts_lang_id"]
        self.assertEqual(dc["mixed"], 38)
        self.assertEqual(dc["separated"], 39)

    # --- RQ39 reproducibility (the H64a baseline must reproduce RQ39)
    def test_rq39_cpwer_reproduced(self) -> None:
        chk = self.data["reproducibility_checks"]["rq39"]
        self.assertTrue(chk["reproduces_rq39_cpwer"])
        self.assertAlmostEqual(
            chk["lang_id_corrected_cpwer"], 1.04329, places=4
        )

    def test_rq39_bca_ci_reproduced(self) -> None:
        chk = self.data["reproducibility_checks"]["rq39"]
        self.assertTrue(chk["reproduces_rq39_bca_ci"])
        ci = chk["lang_id_bca_ci"]
        self.assertAlmostEqual(ci[0], 1.012987, places=4)
        self.assertAlmostEqual(ci[1], 1.097403, places=4)

    # --- RQ58 KL reproducibility
    def test_rq58_kl_section_present(self) -> None:
        self.assertIsNotNone(self.data["kl_corrected_router"])
        self.assertIsNotNone(self.data["reproducibility_checks"]["rq58"])

    def test_rq58_kl_cpwer_reproduced(self) -> None:
        chk = self.data["reproducibility_checks"]["rq58"]
        self.assertTrue(chk["reproduces_rq58_cpwer"])
        self.assertAlmostEqual(
            chk["kl_corrected_cpwer"], 1.030303, places=4
        )

    def test_rq58_kl_bca_ci_reproduced(self) -> None:
        chk = self.data["reproducibility_checks"]["rq58"]
        self.assertTrue(chk["reproduces_rq58_bca_ci"])
        ci = chk["kl_bca_ci"]
        self.assertAlmostEqual(ci[0], 1.006494, places=4)
        self.assertAlmostEqual(ci[1], 1.077922, places=4)

    # --- H64a: baseline (n=77) BCa CI includes oracle
    def test_h64a_lang_id_supported(self) -> None:
        lang = self.data["lang_id_corrected_router"]
        h = lang["hypothesis_verdicts"]["H64a"]
        self.assertTrue(h["supported"], msg=h["reason"])
        self.assertTrue(h["oracle_inside_ci"])

    def test_h64a_kl_supported(self) -> None:
        kl = self.data["kl_corrected_router"]
        h = kl["hypothesis_verdicts"]["H64a"]
        self.assertTrue(h["supported"], msg=h["reason"])
        self.assertTrue(h["oracle_inside_ci"])

    # --- H64b: required n to exclude oracle
    def test_h64b_lang_id_min_n_is_finite_and_in_grid(self) -> None:
        lang = self.data["lang_id_corrected_router"]
        min_n = lang["min_n_to_exclude_oracle_bca"]
        self.assertIsNotNone(min_n)
        self.assertIn(min_n, mod.N_GRID_FINE)

    def test_h64b_kl_min_n_is_finite_and_in_grid(self) -> None:
        kl = self.data["kl_corrected_router"]
        min_n = kl["min_n_to_exclude_oracle_bca"]
        self.assertIsNotNone(min_n)
        self.assertIn(min_n, mod.N_GRID_FINE)

    def test_h64b_kl_min_n_ge_lang_id_min_n(self) -> None:
        # KL has a smaller gap to oracle (0.013 vs 0.026) so it needs MORE
        # windows to exclude the oracle (CI must shrink further to reveal the
        # smaller gap).
        lang_min = self.data["lang_id_corrected_router"]["min_n_to_exclude_oracle_bca"]
        kl_min = self.data["kl_corrected_router"]["min_n_to_exclude_oracle_bca"]
        self.assertGreaterEqual(kl_min, lang_min)

    # --- H64c: effect size
    def test_h64c_lang_id_effect_size_matches_rq39(self) -> None:
        lang = self.data["lang_id_corrected_router"]
        # 1.04329 - 1.017316 = 0.025974
        self.assertAlmostEqual(lang["effect_size"], 0.025974, places=4)

    def test_h64c_kl_effect_size_matches_rq58(self) -> None:
        kl = self.data["kl_corrected_router"]
        # 1.030303 - 1.017316 = 0.012987
        self.assertAlmostEqual(kl["effect_size"], 0.012987, places=4)

    def test_h64c_lang_id_killed(self) -> None:
        # Effect size 0.026 >= 0.01 -> KILLED (gap is real, not negligible).
        lang = self.data["lang_id_corrected_router"]
        h = lang["hypothesis_verdicts"]["H64c"]
        self.assertFalse(h["supported"], msg=h["reason"])

    def test_h64c_kl_killed(self) -> None:
        # Effect size 0.013 >= 0.01 -> KILLED (gap is real, not negligible).
        kl = self.data["kl_corrected_router"]
        h = kl["hypothesis_verdicts"]["H64c"]
        self.assertFalse(h["supported"], msg=h["reason"])

    # --- overall verdict: sample-size problem (not real ceiling)
    def test_overall_verdict_lang_id_is_sample_size_problem(self) -> None:
        lang = self.data["lang_id_corrected_router"]
        self.assertEqual(lang["overall_verdict"], "sample_size_problem")

    def test_overall_verdict_kl_is_sample_size_problem(self) -> None:
        kl = self.data["kl_corrected_router"]
        self.assertEqual(kl["overall_verdict"], "sample_size_problem")

    # --- extrapolation grid structure
    def test_lang_id_grid_includes_coarse_grid(self) -> None:
        lang = self.data["lang_id_corrected_router"]
        ns = {r["n"] for r in lang["extrapolation_grid"]}
        for n in mod.N_GRID_COARSE:
            self.assertIn(n, ns)

    def test_lang_id_grid_has_fine_grid_size(self) -> None:
        lang = self.data["lang_id_corrected_router"]
        self.assertEqual(
            len(lang["extrapolation_grid"]), len(mod.N_GRID_FINE)
        )

    def test_grid_bca_width_decreases_with_n(self) -> None:
        # BCa CI width should be monotonically non-increasing as n grows
        # (modulo small BCa skew fluctuations). Test the coarse grid where the
        # n-jumps are large enough to dominate any BCa fluctuation.
        lang = self.data["lang_id_corrected_router"]
        coarse = [
            r for r in lang["extrapolation_grid"] if r["n"] in mod.N_GRID_COARSE
        ]
        coarse.sort(key=lambda r: r["n"])
        for i in range(len(coarse) - 1):
            self.assertLessEqual(
                coarse[i + 1]["bca_width"], coarse[i]["bca_width"],
                msg=f"BCa width increased from n={coarse[i]['n']} to n={coarse[i+1]['n']}"
            )

    def test_grid_bca_excludes_oracle_eventually(self) -> None:
        # At the largest n, the BCa CI must exclude the oracle (lower > oracle).
        lang = self.data["lang_id_corrected_router"]
        largest = max(lang["extrapolation_grid"], key=lambda r: r["n"])
        self.assertTrue(largest["excludes_oracle_bca"])
        self.assertGreater(largest["bca_ci"][0], lang["oracle_point"])

    # --- per-window data
    def test_per_window_lang_id_has_77_rows(self) -> None:
        self.assertEqual(len(self.data["per_window_lang_id"]), 77)

    def test_per_window_lang_id_keys_present(self) -> None:
        r = self.data["per_window_lang_id"][0]
        for k in ("window_id", "lang_id_entropy", "corrected_decision",
                  "corrected_cpwer", "oracle_best_cpwer",
                  "always_mixed_cpwer", "always_separated_cpwer"):
            self.assertIn(k, r)

    def test_per_window_kl_has_77_rows(self) -> None:
        self.assertEqual(len(self.data["per_window_kl"]), 77)

    def test_per_window_kl_keys_present(self) -> None:
        r = self.data["per_window_kl"][0]
        for k in ("window_id", "kl_decision", "kl_cpwer",
                  "oracle_best_cpwer", "kl_score", "kl_flag"):
            self.assertIn(k, r)

    # --- CSV output
    def test_csv_exists_and_has_rows(self) -> None:
        self.assertTrue(self.out_csv.exists())
        import csv as _csv
        with self.out_csv.open(encoding="utf-8") as f:
            rows = list(_csv.DictReader(f))
        # 2 routers x len(N_GRID_FINE) grid points
        self.assertEqual(len(rows), 2 * len(mod.N_GRID_FINE))

    def test_csv_has_required_columns(self) -> None:
        import csv as _csv
        with self.out_csv.open(encoding="utf-8") as f:
            reader = _csv.DictReader(f)
            cols = reader.fieldnames
        for c in ("router", "n", "theta_hat", "oracle_point", "effect_size",
                  "bca_ci_lo", "bca_ci_hi", "bca_width",
                  "bca_lower_above_oracle", "oracle_inside_bca_ci"):
            self.assertIn(c, cols)

    def test_csv_contains_both_routers(self) -> None:
        import csv as _csv
        with self.out_csv.open(encoding="utf-8") as f:
            routers = {row["router"] for row in _csv.DictReader(f)}
        self.assertEqual(routers, {"lang_id_corrected", "kl_corrected"})


if __name__ == "__main__":
    unittest.main()
