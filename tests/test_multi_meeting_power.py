"""Tests for RQ68: multi-meeting power simulation for oracle exclusion.

Pin the PURE helpers used by
``results/frontier/multi_meeting_power_simulation/analysis.py``: detector
primitives (script_category, language_id_entropy, max_across_speakers,
corrected_router_decision), bootstrap helpers lifted from RQ39/RQ64
(bootstrap_indices, bootstrap_distribution, percentile_ci, _jackknife_means,
bca_ci), and the NEW RQ68 multi-meeting helpers (draw_meeting,
meeting_bca_ci, primary_meeting_bca_at_n, power_at_n, find_n_star_for_power,
ci_includes_value, compute_effect_size).

The integration test runs the full analysis and asserts the output JSON is
well-formed, the n=77 BCa CI reproduces RQ39 bit-for-bit (integrity check),
and the hypothesis verdicts are internally consistent. No MeetEval is
required (RQ68 uses stored word-level cpWER only). Synthetic data for the
pure helpers -- no AISHELL-4 file, no Whisper, no audio, no LLM.
"""
from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path

import numpy as np

# MeetEval is not required for RQ68 (uses stored cpWER only), but the project
# convention is to guard the import in case the test environment has it.
try:  # noqa: SIM105
    import meeteval  # noqa: F401
    MEETEVAL_AVAILABLE = True
except ImportError:
    MEETEVAL_AVAILABLE = False

# Load the analysis module from the results/frontier path (it is a standalone
# script, not under src/).
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = (
    _PROJECT_ROOT
    / "results"
    / "frontier"
    / "multi_meeting_power_simulation"
    / "analysis.py"
)
_spec = importlib.util.spec_from_file_location(
    "multi_meeting_power_analysis", _MODULE_PATH
)
assert _spec is not None and _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


# =================================================================== script_category
class ScriptCategoryTest(unittest.TestCase):
    """RQ13 detector primitive -- must classify Unicode scripts correctly."""

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

    def test_hiragana_is_hiragana(self) -> None:
        self.assertEqual(mod.script_category("ひ"), "Hiragana")

    def test_punctuation_is_punct(self) -> None:
        self.assertEqual(mod.script_category(","), "Punct")
        self.assertEqual(mod.script_category("!"), "Punct")


# ============================================================ language_id_entropy
class LanguageIdEntropyTest(unittest.TestCase):
    """RQ13 lang-id entropy detector -- clean Chinese ~ 0, diverse > threshold."""

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

    def test_entropy_is_non_negative(self) -> None:
        for text in ["", "商", "abc", "商 abc カ メ 12"]:
            self.assertGreaterEqual(mod.language_id_entropy(text), 0.0)

    def test_entropy_of_pure_digit_string_is_near_zero(self) -> None:
        self.assertLess(mod.language_id_entropy("1234567890"), 0.05)


# ============================================================ max_across_speakers
class MaxAcrossSpeakersTest(unittest.TestCase):
    def test_returns_max_of_fn_over_speakers(self) -> None:
        window = {"separated_text_per_speaker": {"a": "商", "b": "abc"}}
        ent = mod.max_across_speakers(window, mod.language_id_entropy)
        self.assertLess(ent, 0.05)

    def test_returns_high_entropy_when_any_speaker_diverse(self) -> None:
        window = {"separated_text_per_speaker": {"a": "商", "b": "商 abc カ メ"}}
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

    def test_takes_max_not_mean(self) -> None:
        # one clean speaker + one diverse speaker -> should return the diverse
        # speaker's entropy, not the mean
        window = {"separated_text_per_speaker": {"a": "商", "b": "商 abc カ メ 12"}}
        ent = mod.max_across_speakers(window, mod.language_id_entropy)
        ent_b = mod.language_id_entropy("商 abc カ メ 12")
        self.assertAlmostEqual(ent, ent_b, places=6)


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

    def test_missing_speakers_routes_to_separated(self) -> None:
        # no separated_text_per_speaker key -> max_across_speakers returns 0
        # -> 0 is NOT > 0.38 -> "separated"
        self.assertEqual(mod.corrected_router_decision({}), "separated")


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

    def test_alpha_half_gives_2_5_and_97_5_percentiles(self) -> None:
        boot = np.linspace(0.0, 100.0, 1001)
        lo, hi = mod.percentile_ci(boot, alpha=0.05)
        self.assertAlmostEqual(lo, 2.5, delta=0.5)
        self.assertAlmostEqual(hi, 97.5, delta=0.5)

    def test_narrower_alpha_gives_wider_ci(self) -> None:
        boot = np.random.default_rng(1).normal(loc=0.0, scale=1.0, size=50000)
        lo5, hi5 = mod.percentile_ci(boot, alpha=0.05)
        lo1, hi1 = mod.percentile_ci(boot, alpha=0.01)
        self.assertLess(lo1, lo5)
        self.assertGreater(hi1, hi5)


# ============================================================ _jackknife_means
class JackknifeMeansTest(unittest.TestCase):
    def test_length_matches_input(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        jack = mod._jackknife_means(values)
        self.assertEqual(len(jack), len(values))

    def test_each_jackknife_mean_excludes_one_value(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        jack = mod._jackknife_means(values)
        # leave-one-out mean for index 0 = mean of [2,3,4,5] = 3.5
        self.assertAlmostEqual(float(jack[0]), 3.5, places=6)
        # leave-one-out mean for index 4 = mean of [1,2,3,4] = 2.5
        self.assertAlmostEqual(float(jack[4]), 2.5, places=6)

    def test_mean_of_jackknife_equals_sample_mean(self) -> None:
        values = np.array([0.5, 1.5, 2.5, 3.5, 4.5, 5.5])
        jack = mod._jackknife_means(values)
        # Efron-Tibshirani identity: mean of jackknife means = sample mean
        self.assertAlmostEqual(float(jack.mean()), float(values.mean()), places=6)

    def test_single_value_returns_array_of_one(self) -> None:
        values = np.array([42.0])
        jack = mod._jackknife_means(values)
        self.assertEqual(len(jack), 1)
        self.assertAlmostEqual(float(jack[0]), 42.0, places=6)


# ============================================================ bca_ci
class BcaCITest(unittest.TestCase):
    def test_returns_tuple_of_two_floats(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        boot = mod.bootstrap_distribution(values, n_boot=500, seed=42)
        ci = mod.bca_ci(values, boot, alpha=0.05)
        self.assertEqual(len(ci), 2)
        self.assertIsInstance(ci[0], float)
        self.assertIsInstance(ci[1], float)

    def test_lo_le_hi(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        boot = mod.bootstrap_distribution(values, n_boot=500, seed=42)
        lo, hi = mod.bca_ci(values, boot, alpha=0.05)
        self.assertLessEqual(lo, hi)

    def test_ci_brackets_sample_mean(self) -> None:
        values = np.array([0.5, 1.2, 2.8, 3.1, 4.4, 5.6, 6.7, 7.9, 8.8, 9.5])
        boot = mod.bootstrap_distribution(values, n_boot=5000, seed=42)
        lo, hi = mod.bca_ci(values, boot, alpha=0.05)
        self.assertLessEqual(lo, float(values.mean()))
        self.assertGreaterEqual(hi, float(values.mean()))

    def test_constant_data_returns_point(self) -> None:
        # constant data -> no variability -> BCa should collapse to the constant
        values = np.array([3.0] * 10)
        boot = mod.bootstrap_distribution(values, n_boot=200, seed=42)
        lo, hi = mod.bca_ci(values, boot, alpha=0.05)
        self.assertAlmostEqual(lo, 3.0, places=6)
        self.assertAlmostEqual(hi, 3.0, places=6)

    def test_single_value_returns_pair(self) -> None:
        values = np.array([5.0])
        boot = np.array([5.0, 5.0, 5.0])
        lo, hi = mod.bca_ci(values, boot, alpha=0.05)
        self.assertAlmostEqual(lo, 5.0, places=6)
        self.assertAlmostEqual(hi, 5.0, places=6)

    def test_deterministic_with_seed(self) -> None:
        values = np.array([0.1, 0.5, 0.9, 1.2, 0.3, 0.7, 1.1, 0.4])
        boot_a = mod.bootstrap_distribution(values, n_boot=500, seed=42)
        boot_b = mod.bootstrap_distribution(values, n_boot=500, seed=42)
        ci_a = mod.bca_ci(values, boot_a, alpha=0.05)
        ci_b = mod.bca_ci(values, boot_b, alpha=0.05)
        self.assertAlmostEqual(ci_a[0], ci_b[0], places=9)
        self.assertAlmostEqual(ci_a[1], ci_b[1], places=9)


# ============================================================ draw_meeting (NEW RQ68)
class DrawMeetingTest(unittest.TestCase):
    """RQ68 outer resample: draw ONE synthetic meeting of size n from F_hat."""

    def test_returns_array_of_length_n(self) -> None:
        pop = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        meeting = mod.draw_meeting(pop, n_target=50, meeting_seed=42)
        self.assertEqual(len(meeting), 50)

    def test_values_come_from_population(self) -> None:
        pop = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        meeting = mod.draw_meeting(pop, n_target=200, meeting_seed=1)
        for v in meeting:
            self.assertIn(float(v), set(float(x) for x in pop))

    def test_deterministic_with_seed(self) -> None:
        pop = np.array([0.5, 1.5, 2.5, 3.5, 4.5])
        a = mod.draw_meeting(pop, n_target=30, meeting_seed=42)
        b = mod.draw_meeting(pop, n_target=30, meeting_seed=42)
        np.testing.assert_array_equal(a, b)

    def test_different_seeds_usually_differ(self) -> None:
        pop = np.array([0.5, 1.5, 2.5, 3.5, 4.5])
        a = mod.draw_meeting(pop, n_target=100, meeting_seed=1)
        b = mod.draw_meeting(pop, n_target=100, meeting_seed=2)
        self.assertFalse(np.array_equal(a, b))

    def test_n_larger_than_population_is_allowed(self) -> None:
        # resample WITH replacement -> n_target can exceed len(pop)
        pop = np.array([1.0, 2.0, 3.0])
        meeting = mod.draw_meeting(pop, n_target=500, meeting_seed=7)
        self.assertEqual(len(meeting), 500)

    def test_n_target_below_one_raises(self) -> None:
        pop = np.array([1.0, 2.0, 3.0])
        with self.assertRaises(ValueError):
            mod.draw_meeting(pop, n_target=0, meeting_seed=42)


# ============================================================ meeting_bca_ci
class MeetingBcaCiTest(unittest.TestCase):
    """RQ68 inner BCa CI on a single simulated meeting's data."""

    def test_returns_expected_keys(self) -> None:
        meeting = np.array([1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9])
        r = mod.meeting_bca_ci(meeting, n_boot=500, boot_seed=42)
        for k in ("meeting_mean", "bca_ci", "pct_ci", "bca_width", "pct_width"):
            self.assertIn(k, r)

    def test_meeting_mean_is_sample_mean(self) -> None:
        meeting = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
        r = mod.meeting_bca_ci(meeting, n_boot=200, boot_seed=1)
        self.assertAlmostEqual(r["meeting_mean"], float(meeting.mean()), places=9)

    def test_bca_ci_brackets_meeting_mean(self) -> None:
        meeting = np.array([0.5, 1.2, 2.8, 3.1, 4.4, 5.6, 6.7, 7.9, 8.8, 9.5])
        r = mod.meeting_bca_ci(meeting, n_boot=2000, boot_seed=42)
        lo, hi = r["bca_ci"]
        self.assertLessEqual(lo, r["meeting_mean"])
        self.assertGreaterEqual(hi, r["meeting_mean"])

    def test_bca_width_is_hi_minus_lo(self) -> None:
        meeting = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        r = mod.meeting_bca_ci(meeting, n_boot=500, boot_seed=3)
        lo, hi = r["bca_ci"]
        self.assertAlmostEqual(r["bca_width"], hi - lo, places=9)

    def test_deterministic_with_seed(self) -> None:
        meeting = np.array([0.1, 0.5, 0.9, 1.2, 0.3, 0.7, 1.1, 0.4])
        a = mod.meeting_bca_ci(meeting, n_boot=500, boot_seed=42)
        b = mod.meeting_bca_ci(meeting, n_boot=500, boot_seed=42)
        self.assertAlmostEqual(a["bca_ci"][0], b["bca_ci"][0], places=9)
        self.assertAlmostEqual(a["bca_ci"][1], b["bca_ci"][1], places=9)

    def test_larger_n_gives_narrower_ci(self) -> None:
        # bigger meeting -> tighter CI (standard sqrt(n) shrinkage)
        pop = np.array([1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4])
        small = mod.draw_meeting(pop, 20, meeting_seed=11)
        big = mod.draw_meeting(pop, 500, meeting_seed=12)
        r_small = mod.meeting_bca_ci(small, n_boot=1000, boot_seed=42)
        r_big = mod.meeting_bca_ci(big, n_boot=1000, boot_seed=42)
        self.assertLess(r_big["bca_width"], r_small["bca_width"])

    def test_single_value_returns_point(self) -> None:
        meeting = np.array([5.0])
        r = mod.meeting_bca_ci(meeting, n_boot=100, boot_seed=1)
        self.assertAlmostEqual(r["meeting_mean"], 5.0, places=6)
        self.assertAlmostEqual(r["bca_ci"][0], 5.0, places=6)
        self.assertAlmostEqual(r["bca_ci"][1], 5.0, places=6)


# ============================================================ primary_meeting_bca_at_n
class PrimaryMeetingBcaAtNTest(unittest.TestCase):
    """RQ68 headline primary meeting BCa CI at a target n."""

    def test_returns_expected_keys(self) -> None:
        pop = np.array([1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9])
        r = mod.primary_meeting_bca_at_n(pop, n_target=50, n_boot=500,
                                          meeting_seed=42, boot_seed=42)
        for k in ("meeting_mean", "bca_ci", "pct_ci", "bca_width", "pct_width",
                  "n", "population_mean", "meeting_size"):
            self.assertIn(k, r)

    def test_n_is_target_n(self) -> None:
        pop = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        r = mod.primary_meeting_bca_at_n(pop, n_target=77, n_boot=200,
                                          meeting_seed=42, boot_seed=42)
        self.assertEqual(r["n"], 77)
        self.assertEqual(r["meeting_size"], 77)

    def test_population_mean_is_population_mean(self) -> None:
        pop = np.array([0.5, 1.0, 1.5, 2.0, 2.5])
        r = mod.primary_meeting_bca_at_n(pop, n_target=30, n_boot=200,
                                          meeting_seed=1, boot_seed=2)
        self.assertAlmostEqual(r["population_mean"], float(pop.mean()), places=9)

    def test_deterministic_with_seed(self) -> None:
        pop = np.array([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5])
        a = mod.primary_meeting_bca_at_n(pop, n_target=40, n_boot=500,
                                          meeting_seed=42, boot_seed=42)
        b = mod.primary_meeting_bca_at_n(pop, n_target=40, n_boot=500,
                                          meeting_seed=42, boot_seed=42)
        self.assertAlmostEqual(a["bca_ci"][0], b["bca_ci"][0], places=9)
        self.assertAlmostEqual(a["bca_ci"][1], b["bca_ci"][1], places=9)

    def test_uses_default_seeds_when_omitted(self) -> None:
        pop = np.array([1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4])
        a = mod.primary_meeting_bca_at_n(pop, n_target=50, n_boot=500)
        b = mod.primary_meeting_bca_at_n(pop, n_target=50, n_boot=500,
                                          meeting_seed=mod.PRIMARY_MEETING_SEED,
                                          boot_seed=mod.PRIMARY_BOOT_SEED)
        self.assertAlmostEqual(a["bca_ci"][0], b["bca_ci"][0], places=9)


# ============================================================ power_at_n
class PowerAtNTest(unittest.TestCase):
    """RQ68 simulated power = fraction of M meetings whose BCa CI excludes oracle."""

    def test_returns_expected_keys(self) -> None:
        pop = np.array([1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9])
        r = mod.power_at_n(pop, n_target=50, oracle=0.95,
                            n_meetings=20, n_boot=200, base_seed=42)
        for k in ("n", "n_meetings", "n_boot", "power", "excludes_count",
                  "oracle_point", "median_bca_ci_lo", "median_bca_ci_hi",
                  "median_bca_excludes_oracle", "mean_bca_lo", "mean_bca_hi",
                  "mean_meeting_mean", "std_meeting_mean"):
            self.assertIn(k, r)

    def test_power_in_zero_one(self) -> None:
        pop = np.array([1.0, 1.5, 2.0, 2.5, 3.0])
        r = mod.power_at_n(pop, n_target=40, oracle=0.0,
                            n_meetings=30, n_boot=200, base_seed=1)
        # oracle=0 -> every CI excludes (all values > 0) -> power = 1.0
        self.assertEqual(r["power"], 1.0)
        self.assertEqual(r["excludes_count"], 30)

    def test_power_zero_when_oracle_above_all(self) -> None:
        pop = np.array([1.0, 1.1, 1.2, 1.3, 1.4])
        r = mod.power_at_n(pop, n_target=40, oracle=100.0,
                            n_meetings=20, n_boot=200, base_seed=1)
        # oracle=100 -> no CI can exclude (all means < 100) -> power = 0.0
        self.assertEqual(r["power"], 0.0)
        self.assertEqual(r["excludes_count"], 0)

    def test_excludes_count_equals_power_times_m(self) -> None:
        pop = np.array([1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4])
        r = mod.power_at_n(pop, n_target=50, oracle=1.5,
                            n_meetings=40, n_boot=300, base_seed=7)
        self.assertEqual(r["excludes_count"], int(round(r["power"] * 40)))

    def test_deterministic_with_seed(self) -> None:
        pop = np.array([1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4])
        a = mod.power_at_n(pop, n_target=40, oracle=1.5,
                            n_meetings=20, n_boot=300, base_seed=42)
        b = mod.power_at_n(pop, n_target=40, oracle=1.5,
                            n_meetings=20, n_boot=300, base_seed=42)
        self.assertEqual(a["power"], b["power"])
        self.assertEqual(a["excludes_count"], b["excludes_count"])

    def test_larger_n_gives_higher_power(self) -> None:
        # bigger meetings -> tighter CIs -> more likely to exclude oracle
        pop = np.array([1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9])
        oracle = float(pop.mean()) - 0.05  # just below population mean
        r_small = mod.power_at_n(pop, n_target=30, oracle=oracle,
                                   n_meetings=50, n_boot=400, base_seed=42)
        r_big = mod.power_at_n(pop, n_target=300, oracle=oracle,
                                 n_meetings=50, n_boot=400, base_seed=42)
        self.assertGreaterEqual(r_big["power"], r_small["power"])

    def test_n_target_below_two_raises(self) -> None:
        pop = np.array([1.0, 2.0, 3.0])
        with self.assertRaises(ValueError):
            mod.power_at_n(pop, n_target=1, oracle=0.5,
                            n_meetings=10, n_boot=100, base_seed=1)

    def test_n_meetings_below_one_raises(self) -> None:
        pop = np.array([1.0, 2.0, 3.0])
        with self.assertRaises(ValueError):
            mod.power_at_n(pop, n_target=10, oracle=0.5,
                            n_meetings=0, n_boot=100, base_seed=1)


# ============================================================ find_n_star_for_power
class FindNStarForPowerTest(unittest.TestCase):
    """RQ68 find the minimum n where power >= target (linear interpolation)."""

    def test_returns_n_when_power_already_at_target(self) -> None:
        curve = [
            {"n": 50, "power": 0.90},
            {"n": 100, "power": 0.95},
        ]
        self.assertEqual(mod.find_n_star_for_power(curve, target=0.80), 50)

    def test_interpolates_between_grid_points(self) -> None:
        curve = [
            {"n": 100, "power": 0.50},
            {"n": 200, "power": 0.90},
        ]
        # 0.80 is between 0.50 and 0.90 -> interpolate
        # frac = (0.80 - 0.50) / (0.90 - 0.50) = 0.75
        # n* = 100 + 0.75 * (200 - 100) = 175 -> ceil = 175
        self.assertEqual(mod.find_n_star_for_power(curve, target=0.80), 175)

    def test_returns_none_when_power_never_reaches_target(self) -> None:
        curve = [
            {"n": 100, "power": 0.50},
            {"n": 200, "power": 0.60},
            {"n": 300, "power": 0.70},
        ]
        self.assertIsNone(mod.find_n_star_for_power(curve, target=0.80))

    def test_handles_flat_curve_at_target(self) -> None:
        curve = [
            {"n": 100, "power": 0.80},
            {"n": 200, "power": 0.80},
        ]
        self.assertEqual(mod.find_n_star_for_power(curve, target=0.80), 100)

    def test_returns_last_n_if_power_reaches_target_there(self) -> None:
        curve = [
            {"n": 100, "power": 0.50},
            {"n": 200, "power": 0.80},
        ]
        self.assertEqual(mod.find_n_star_for_power(curve, target=0.80), 200)

    def test_handles_unsorted_curve(self) -> None:
        curve = [
            {"n": 200, "power": 0.90},
            {"n": 100, "power": 0.50},
        ]
        # sorted internally -> n=100 power=0.50, n=200 power=0.90
        # 0.80 is between -> interpolate -> frac=0.75 -> n*=175
        self.assertEqual(mod.find_n_star_for_power(curve, target=0.80), 175)

    def test_uses_default_target_0_80(self) -> None:
        curve = [
            {"n": 100, "power": 0.50},
            {"n": 200, "power": 0.85},
        ]
        # default target = 0.80 -> interpolate
        # frac = (0.80 - 0.50) / (0.85 - 0.50) = 0.30/0.35 = 6/7 ~ 0.857
        # n* = 100 + 0.857 * 100 = 185.7 -> ceil = 186
        self.assertEqual(mod.find_n_star_for_power(curve), 186)

    def test_empty_curve_returns_none(self) -> None:
        self.assertIsNone(mod.find_n_star_for_power([], target=0.80))


# ============================================================ ci_includes_value
class CiIncludesValueTest(unittest.TestCase):
    def test_value_inside_ci_returns_true(self) -> None:
        self.assertTrue(mod.ci_includes_value((1.0, 2.0), 1.5))

    def test_value_at_lo_bound_returns_true(self) -> None:
        self.assertTrue(mod.ci_includes_value((1.0, 2.0), 1.0))

    def test_value_at_hi_bound_returns_true(self) -> None:
        self.assertTrue(mod.ci_includes_value((1.0, 2.0), 2.0))

    def test_value_below_lo_returns_false(self) -> None:
        self.assertFalse(mod.ci_includes_value((1.0, 2.0), 0.5))

    def test_value_above_hi_returns_false(self) -> None:
        self.assertFalse(mod.ci_includes_value((1.0, 2.0), 2.5))


# ============================================================ compute_effect_size
class ComputeEffectSizeTest(unittest.TestCase):
    def test_positive_when_corrected_above_oracle(self) -> None:
        # corrected worse than oracle -> positive effect size
        self.assertAlmostEqual(mod.compute_effect_size(1.05, 1.02), 0.03, places=9)

    def test_zero_when_equal(self) -> None:
        self.assertAlmostEqual(mod.compute_effect_size(1.0, 1.0), 0.0, places=9)

    def test_negative_when_corrected_below_oracle(self) -> None:
        # corrected better than oracle -> negative effect size
        self.assertAlmostEqual(mod.compute_effect_size(0.98, 1.02), -0.04, places=9)

    def test_returns_float(self) -> None:
        self.assertIsInstance(mod.compute_effect_size(1.5, 1.0), float)


# ============================================================ integration: constants
class IntegrationConstantsTest(unittest.TestCase):
    """Verify the module-level constants match the pre-registered spec."""

    def test_lang_id_threshold_is_0_38(self) -> None:
        self.assertEqual(mod.LANG_ID_ENTROPY_THRESHOLD, 0.38)

    def test_primary_n_boot_is_10000(self) -> None:
        self.assertEqual(mod.PRIMARY_N_BOOT, 10000)

    def test_primary_seeds_are_42(self) -> None:
        self.assertEqual(mod.PRIMARY_MEETING_SEED, 42)
        self.assertEqual(mod.PRIMARY_BOOT_SEED, 42)

    def test_power_n_meetings_is_200(self) -> None:
        self.assertEqual(mod.POWER_N_MEETINGS, 200)

    def test_power_n_boot_is_2000(self) -> None:
        self.assertEqual(mod.POWER_N_BOOT, 2000)

    def test_alpha_is_0_05(self) -> None:
        self.assertEqual(mod.ALPHA, 0.05)

    def test_n_grid_contains_preregistered_points(self) -> None:
        # H68a point (n=105), H68b point (n=250), RQ64 ceiling (n=770),
        # and baseline (n=77) must all be in the grid.
        for n in (77, 105, 250, 770):
            self.assertIn(n, mod.N_GRID)

    def test_h68c_target_is_0_80(self) -> None:
        self.assertEqual(mod.H68C_POWER_TARGET, 0.80)

    def test_h68c_ceiling_is_770(self) -> None:
        self.assertEqual(mod.H68C_TRACTABLE_CEILING, 770)

    def test_rq64_reference_values(self) -> None:
        self.assertAlmostEqual(mod.RQ39_WORD_CORRECTED_CPWER, 1.04329, places=5)
        self.assertAlmostEqual(mod.RQ39_WORD_ORACLE_CPWER, 1.017316, places=5)
        self.assertAlmostEqual(mod.RQ58_KL_CPWER, 1.030303, places=5)
        self.assertEqual(mod.RQ64_LANG_ID_MIN_N, 105)
        self.assertEqual(mod.RQ64_KL_MIN_N, 250)
        self.assertEqual(mod.RQ64_TRACTABLE_CEILING, 770)


# ============================================================ integration: baseline n=77
class IntegrationBaselineN77Test(unittest.TestCase):
    """Verify the n=77 baseline reproduces RQ39/RQ58 bit-for-bit.

    This is the load-bearing sanity check: if the BCa framework doesn't
    reproduce the source RQs at n=77, the whole multi-meeting simulation
    is invalid. Runs ONLY the n=77 baseline (one bootstrap of 77 values),
    NOT the full power curve -- fast (<1 s).
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(mod.SRC_JSON.read_text(encoding="utf-8"))
        cls.lang_rows = mod._load_corrected_per_window(cls.data)
        cls.lang_arr = np.array(
            [r["corrected_cpwer"] for r in cls.lang_rows], dtype=float
        )
        cls.lang_oracle = float(np.array(
            [r["oracle_best_cpwer"] for r in cls.lang_rows], dtype=float
        ).mean())

    def test_lang_id_cpwer_reproduces_rq39(self) -> None:
        theta = float(self.lang_arr.mean())
        self.assertAlmostEqual(theta, mod.RQ39_WORD_CORRECTED_CPWER, places=4)

    def test_lang_id_bca_ci_reproduces_rq39(self) -> None:
        boot = mod.bootstrap_distribution(
            self.lang_arr, mod.PRIMARY_N_BOOT, mod.PRIMARY_BOOT_SEED
        )
        lo, hi = mod.bca_ci(self.lang_arr, boot, mod.ALPHA)
        self.assertAlmostEqual(lo, mod.RQ39_WORD_BCA_CI[0], places=4)
        self.assertAlmostEqual(hi, mod.RQ39_WORD_BCA_CI[1], places=4)

    def test_lang_id_decision_counts_match_rq39(self) -> None:
        # RQ39: mixed=38, separated=39 (verified in FINDINGS.md section 3.1)
        mixed = sum(1 for r in self.lang_rows if r["corrected_decision"] == "mixed")
        sep = sum(1 for r in self.lang_rows if r["corrected_decision"] == "separated")
        self.assertEqual(mixed, 38)
        self.assertEqual(sep, 39)
        self.assertEqual(mixed + sep, 77)

    def test_lang_id_oracle_inside_bca_ci_at_n77(self) -> None:
        # RQ64's H64a: at n=77 the BCa CI INCLUDES the oracle
        boot = mod.bootstrap_distribution(
            self.lang_arr, mod.PRIMARY_N_BOOT, mod.PRIMARY_BOOT_SEED
        )
        lo, hi = mod.bca_ci(self.lang_arr, boot, mod.ALPHA)
        self.assertTrue(lo <= self.lang_oracle <= hi)

    def test_kl_cpwer_reproduces_rq58_if_available(self) -> None:
        if not mod.KL_JSON.exists():
            self.skipTest("RQ58 KL JSON not available")
        kl_rows = mod._load_kl_per_window()
        self.assertIsNotNone(kl_rows)
        kl_arr = np.array([r["kl_cpwer"] for r in kl_rows], dtype=float)
        self.assertAlmostEqual(float(kl_arr.mean()), mod.RQ58_KL_CPWER, places=4)

    def test_kl_bca_ci_reproduces_rq58_if_available(self) -> None:
        if not mod.KL_JSON.exists():
            self.skipTest("RQ58 KL JSON not available")
        kl_rows = mod._load_kl_per_window()
        kl_arr = np.array([r["kl_cpwer"] for r in kl_rows], dtype=float)
        boot = mod.bootstrap_distribution(
            kl_arr, mod.PRIMARY_N_BOOT, mod.PRIMARY_BOOT_SEED
        )
        lo, hi = mod.bca_ci(kl_arr, boot, mod.ALPHA)
        self.assertAlmostEqual(lo, mod.RQ58_KL_BCA_CI[0], places=4)
        self.assertAlmostEqual(hi, mod.RQ58_KL_BCA_CI[1], places=4)


# ============================================================ integration: committed JSON
class IntegrationCommittedJsonTest(unittest.TestCase):
    """Verify the committed results JSON is well-formed and internally
    consistent with the pre-registered hypothesis verdicts.

    Reads the committed ``multi_meeting_power_results.json`` (produced by
    ``analysis.py``) and asserts the hypothesis verdicts match the
    pre-registered KILL conditions. Does NOT re-run the analysis.
    """

    @classmethod
    def setUpClass(cls) -> None:
        if not mod.OUT_JSON.exists():
            raise unittest.SkipTest(
                f"Committed results JSON not found at {mod.OUT_JSON}"
            )
        cls.summary = json.loads(mod.OUT_JSON.read_text(encoding="utf-8"))

    def test_label_is_experimental_frontier(self) -> None:
        self.assertEqual(self.summary["label"], "experimental/frontier")

    def test_closes_issue_996(self) -> None:
        self.assertEqual(self.summary["closes_issue"], 996)

    def test_n_windows_is_77(self) -> None:
        self.assertEqual(self.summary["n_windows"], 77)

    def test_lang_id_router_present(self) -> None:
        self.assertIsNotNone(self.summary["lang_id_corrected_router"])

    def test_kl_router_present(self) -> None:
        # KL analysis requires RQ58's JSON; skip if absent
        if not mod.KL_JSON.exists():
            self.skipTest("RQ58 KL JSON not available")
        self.assertIsNotNone(self.summary["kl_corrected_router"])

    def test_lang_id_per_n_has_9_grid_points(self) -> None:
        per_n = self.summary["lang_id_corrected_router"]["per_n"]
        self.assertEqual(len(per_n), len(mod.N_GRID))
        for r, expected_n in zip(per_n, mod.N_GRID):
            self.assertEqual(r["n"], expected_n)

    def test_lang_id_reproduces_rq39_at_baseline(self) -> None:
        repro = self.summary["reproducibility_checks"]["rq39"]
        self.assertTrue(repro["reproduces_rq39_cpwer"])
        self.assertTrue(repro["reproduces_rq39_bca_ci"])

    def test_kl_reproduces_rq58_at_baseline_if_available(self) -> None:
        repro = self.summary["reproducibility_checks"].get("rq58")
        if repro is None:
            self.skipTest("RQ58 KL reproducibility check not present")
        self.assertTrue(repro["reproduces_rq58_cpwer"])
        self.assertTrue(repro["reproduces_rq58_bca_ci"])

    def test_h68a_verdict_matches_preregistration(self) -> None:
        """H68a: n=105 lang-id primary BCa CI. KILL if includes oracle.

        Per FINDINGS.md section 4.4: H68a is KILLED (primary meeting at
        n=105 includes oracle 1.017316). This test pins that honest verdict.
        """
        h = self.summary["lang_id_corrected_router"]["hypothesis_verdicts"]["H68"]
        # The verdict must be internally consistent: supported flag matches
        # whether the primary BCa CI excludes the oracle.
        self.assertEqual(
            h["supported"], h["primary_excludes_oracle"],
            "H68a supported flag must match primary_excludes_oracle"
        )
        # Pin the honest KILLED verdict (FINDINGS.md section 4.4 / 5.1)
        self.assertFalse(h["supported"], "H68a must be KILLED per FINDINGS.md")
        # The primary BCa CI at n=105 must include the oracle
        lo, hi = h["primary_bca_ci_at_rq64_n"]
        oracle = h["oracle_point"]
        self.assertLessEqual(lo, oracle, "H68a CI lower bound must be <= oracle")
        self.assertGreaterEqual(hi, oracle, "H68a CI upper bound must be >= oracle")

    def test_h68b_verdict_matches_preregistration(self) -> None:
        """H68b: n=250 KL primary BCa CI. KILL if includes oracle.

        Per FINDINGS.md section 4.4: H68b is SUPPORTED (primary meeting at
        n=250 excludes oracle 1.017316 by 0.000017). This test pins that
        verdict and verifies internal consistency.
        """
        kl = self.summary.get("kl_corrected_router")
        if kl is None:
            self.skipTest("KL router analysis not present")
        h = kl["hypothesis_verdicts"]["H68"]
        self.assertEqual(
            h["supported"], h["primary_excludes_oracle"],
            "H68b supported flag must match primary_excludes_oracle"
        )
        # Pin the SUPPORTED verdict (FINDINGS.md section 4.4 / 5.2)
        self.assertTrue(h["supported"], "H68b must be SUPPORTED per FINDINGS.md")
        lo, hi = h["primary_bca_ci_at_rq64_n"]
        oracle = h["oracle_point"]
        self.assertGreater(lo, oracle, "H68b CI lower bound must be > oracle")

    def test_h68c_verdict_matches_preregistration(self) -> None:
        """H68c: power reaches 80% at n <= 770. KILL if n* > 770.

        Per FINDINGS.md section 4.4: H68c is SUPPORTED for both routers
        (lang-id n*=234, KL n*=680, both <= 770).
        """
        for router_key in ("lang_id_corrected_router", "kl_corrected_router"):
            router = self.summary.get(router_key)
            if router is None:
                continue
            h = router["hypothesis_verdicts"]["H68c"]
            self.assertTrue(h["supported"],
                            f"H68c must be SUPPORTED for {router_key}")
            self.assertLessEqual(
                h["n_star_80pct"], h["tractable_ceiling"],
                f"H68c n* must be <= ceiling for {router_key}"
            )

    def test_lang_id_n_star_is_234(self) -> None:
        """Pin the lang-id n* = 234 (FINDINGS.md section 4.2)."""
        n_star = self.summary["lang_id_corrected_router"]["n_star_80pct"]
        self.assertEqual(n_star, 234)

    def test_kl_n_star_is_680_if_available(self) -> None:
        """Pin the KL n* = 680 (FINDINGS.md section 4.3)."""
        kl = self.summary.get("kl_corrected_router")
        if kl is None:
            self.skipTest("KL router analysis not present")
        self.assertEqual(kl["n_star_80pct"], 680)

    def test_lang_id_power_monotone_nondecreasing(self) -> None:
        """Power curve should be (weakly) monotone nondecreasing in n."""
        per_n = self.summary["lang_id_corrected_router"]["per_n"]
        powers = [r["power"] for r in per_n]
        for i in range(len(powers) - 1):
            self.assertGreaterEqual(
                powers[i + 1], powers[i] - 0.05,
                f"Power dropped from n={per_n[i]['n']} to n={per_n[i+1]['n']}"
            )

    def test_lang_id_power_reaches_1_at_n770(self) -> None:
        per_n = self.summary["lang_id_corrected_router"]["per_n"]
        row_770 = next(r for r in per_n if r["n"] == 770)
        self.assertEqual(row_770["power"], 1.0)

    def test_csv_has_18_rows_plus_header(self) -> None:
        """CSV: 2 routers x 9 grid points = 18 data rows + 1 header."""
        if not mod.OUT_CSV.exists():
            self.skipTest("Committed CSV not found")
        with mod.OUT_CSV.open(encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 19)  # 1 header + 18 data


# ============================================================ integration: pipeline
class IntegrationPipelineTest(unittest.TestCase):
    """End-to-end pipeline test on SYNTHETIC data.

    Runs the full ``_run_multi_meeting_analysis`` driver on a small synthetic
    population (30 values, 3 grid points) to verify the pipeline produces a
    well-formed result dict with internally consistent hypothesis verdicts.
    Uses the production M=200 / B=2000 settings (same as the real analysis)
    so the test exercises the actual code path; the small grid keeps runtime
    to a few seconds.
    """

    @classmethod
    def setUpClass(cls) -> None:
        # Synthetic population: 30 values, mean ~1.05, oracle ~1.00
        # -> effect size 0.05, should exclude oracle at moderate n.
        rng = np.random.default_rng(123)
        cls.pop = rng.normal(loc=1.05, scale=0.10, size=30)
        cls.oracle = 1.00
        cls.analysis = mod._run_multi_meeting_analysis(
            name="synthetic_test_router",
            per_window_cpwer=cls.pop,
            oracle_point=cls.oracle,
            n_grid=[30, 60, 120],
            rq64_min_n=60,
        )

    def test_returns_expected_top_level_keys(self) -> None:
        for k in ("name", "n_population", "theta_hat", "oracle_point",
                  "effect_size", "rq64_min_n_prediction", "baseline_n77",
                  "per_n", "n_star_80pct", "rq64_comparison",
                  "hypothesis_verdicts"):
            self.assertIn(k, self.analysis)

    def test_n_population_matches_input(self) -> None:
        self.assertEqual(self.analysis["n_population"], 30)

    def test_theta_hat_is_population_mean(self) -> None:
        self.assertAlmostEqual(
            self.analysis["theta_hat"], float(self.pop.mean()), places=4
        )

    def test_effect_size_is_theta_minus_oracle(self) -> None:
        expected = float(self.pop.mean()) - self.oracle
        self.assertAlmostEqual(self.analysis["effect_size"], expected, places=4)

    def test_per_n_length_matches_grid(self) -> None:
        self.assertEqual(len(self.analysis["per_n"]), 3)

    def test_per_n_has_expected_keys(self) -> None:
        for r in self.analysis["per_n"]:
            for k in ("n", "primary_meeting_mean", "primary_bca_ci",
                      "primary_pct_ci", "primary_bca_width",
                      "primary_bca_excludes_oracle",
                      "oracle_inside_primary_bca_ci", "power",
                      "power_excludes_count", "power_n_meetings",
                      "power_n_boot", "median_bca_ci",
                      "median_bca_excludes_oracle", "mean_bca_ci",
                      "mean_meeting_mean", "std_meeting_mean"):
                self.assertIn(k, r)

    def test_hypothesis_verdicts_have_h68_and_h68c(self) -> None:
        hv = self.analysis["hypothesis_verdicts"]
        self.assertIn("H68", hv)
        self.assertIn("H68c", hv)

    def test_h68_supported_matches_primary_excludes(self) -> None:
        h = self.analysis["hypothesis_verdicts"]["H68"]
        self.assertEqual(h["supported"], h["primary_excludes_oracle"])

    def test_h68c_supported_matches_n_star_le_ceiling(self) -> None:
        h = self.analysis["hypothesis_verdicts"]["H68c"]
        if h["n_star_80pct"] is not None:
            expected = h["n_star_80pct"] <= h["tractable_ceiling"]
            self.assertEqual(h["supported"], expected)

    def test_baseline_bca_ci_brackets_theta_hat(self) -> None:
        bl = self.analysis["baseline_n77"]
        lo, hi = bl["bca_ci_95"]
        self.assertLessEqual(lo, self.analysis["theta_hat"])
        self.assertGreaterEqual(hi, self.analysis["theta_hat"])

    def test_baseline_reproduces_standard_bootstrap(self) -> None:
        # The baseline n=77 (here n=30) BCa CI must equal the standard
        # bootstrap BCa CI on the population (theta_hat = pop mean).
        bl = self.analysis["baseline_n77"]
        boot = mod.bootstrap_distribution(
            self.pop, mod.PRIMARY_N_BOOT, mod.PRIMARY_BOOT_SEED
        )
        lo, hi = mod.bca_ci(self.pop, boot, mod.ALPHA)
        self.assertAlmostEqual(bl["bca_ci_95"][0], lo, places=4)
        self.assertAlmostEqual(bl["bca_ci_95"][1], hi, places=4)


# ============================================================ integration: H68c logic
class IntegrationH68cLogicTest(unittest.TestCase):
    """Verify find_n_star_for_power agrees with the H68c verdict logic."""

    def test_n_star_below_ceiling_means_supported(self) -> None:
        curve = [{"n": n, "power": p} for n, p in [
            (100, 0.50), (200, 0.70), (300, 0.85), (500, 0.95)
        ]]
        n_star = mod.find_n_star_for_power(curve, target=0.80)
        # n* should be between 200 and 300
        self.assertIsNotNone(n_star)
        self.assertLess(n_star, 300)
        self.assertGreater(n_star, 200)
        self.assertLessEqual(n_star, mod.H68C_TRACTABLE_CEILING)

    def test_n_star_above_ceiling_means_killed(self) -> None:
        # Construct a curve that only reaches 0.80 at n=1000 (> 770 ceiling)
        curve = [{"n": n, "power": p} for n, p in [
            (100, 0.10), (250, 0.20), (500, 0.40), (770, 0.60), (1000, 0.85)
        ]]
        n_star = mod.find_n_star_for_power(curve, target=0.80)
        self.assertIsNotNone(n_star)
        self.assertGreater(n_star, mod.H68C_TRACTABLE_CEILING)

    def test_power_never_reaching_80_means_killed(self) -> None:
        curve = [{"n": n, "power": p} for n, p in [
            (100, 0.30), (500, 0.50), (770, 0.65), (1000, 0.70)
        ]]
        n_star = mod.find_n_star_for_power(curve, target=0.80)
        self.assertIsNone(n_star)


if __name__ == "__main__":
    unittest.main()