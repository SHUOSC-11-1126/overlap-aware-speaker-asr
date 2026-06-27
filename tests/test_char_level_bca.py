"""Tests for RQ55: char-level BCa CI on the corrected router (experimental/frontier).

Pin the PURE helpers used by
``results/frontier/char_level_bca/char_level_bca_analysis.py``:
detector primitives (script_category, language_id_entropy, max_across_speakers,
corrected_router_decision), char-level MeetEval helpers (to_char_level,
build_segments, build_mixed_segment, safe_cpwer, safe_orcwer), and bootstrap
helpers (bootstrap_indices, bootstrap_distribution, percentile_ci,
_jackknife_means, bca_ci, paired_delta_distribution, paired_delta_ci).

MeetEval-dependent tests (safe_cpwer/safe_orcwer on real Chinese text, and the
full integration test) are guarded by ``HAS_MEETEVAL``. Synthetic data only for
the pure helpers — no AISHELL-4 file, no Whisper, no audio.
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
    / "char_level_bca"
    / "char_level_bca_analysis.py"
)
_spec = importlib.util.spec_from_file_location(
    "char_level_bca_analysis", _MODULE_PATH
)
assert _spec is not None and _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

# MeetEval availability guards the integration + char-level cpWER tests.
HAS_MEETEVAL = importlib.util.find_spec("meeteval") is not None


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
        # "abc" is pure Latin (1 category) -> entropy 0; "商" pure Han -> 0.
        # Both near 0; max should be near 0.
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
        self.assertEqual(mod.max_across_speakers(window, mod.language_id_entropy), 0.0)

    def test_missing_separated_text_returns_zero(self) -> None:
        window = {}
        self.assertEqual(mod.max_across_speakers(window, mod.language_id_entropy), 0.0)


# ====================================================== corrected_router_decision
class CorrectedRouterDecisionTest(unittest.TestCase):
    def test_low_entropy_routes_to_separated(self) -> None:
        window = {"separated_text_per_speaker": {"a": "零零幺商场经理"}}
        self.assertEqual(mod.corrected_router_decision(window), "separated")

    def test_high_entropy_routes_to_mixed(self) -> None:
        window = {"separated_text_per_speaker": {"a": "商 abc 卡 메 12"}}
        self.assertEqual(mod.corrected_router_decision(window), "mixed")

    def test_threshold_0_38_is_used(self) -> None:
        # A window with entropy just above 0.38 should route to MIXED.
        # "商 abc 카 メ" has entropy well above 0.38.
        window = {"separated_text_per_speaker": {"a": "商 abc 카 メ"}}
        self.assertEqual(mod.corrected_router_decision(window), "mixed")

    def test_empty_window_routes_to_separated(self) -> None:
        window = {"separated_text_per_speaker": {"a": ""}}
        self.assertEqual(mod.corrected_router_decision(window), "separated")


# ============================================================ to_char_level
class ToCharLevelTest(unittest.TestCase):
    def test_inserts_space_between_each_char(self) -> None:
        self.assertEqual(mod.to_char_level("你好"), "你 好")

    def test_single_char_no_space(self) -> None:
        self.assertEqual(mod.to_char_level("商"), "商")

    def test_empty_string_returns_empty(self) -> None:
        self.assertEqual(mod.to_char_level(""), "")

    def test_mixed_scripts_each_char_separated(self) -> None:
        self.assertEqual(mod.to_char_level("a商"), "a 商")


# ============================================================ build_segments
class BuildSegmentsTest(unittest.TestCase):
    def test_builds_one_segment_per_nonempty_speaker(self) -> None:
        segs = mod.build_segments({"a": "你好", "b": "世界"})
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[0]["speaker"], "a")
        self.assertEqual(segs[0]["words"], "你 好")
        self.assertEqual(segs[1]["speaker"], "b")
        self.assertEqual(segs[1]["words"], "世 界")

    def test_skips_empty_speakers(self) -> None:
        segs = mod.build_segments({"a": "你好", "b": "", "c": "  "})
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0]["speaker"], "a")

    def test_segment_has_session_id(self) -> None:
        segs = mod.build_segments({"a": "商"})
        self.assertEqual(segs[0]["session_id"], mod.SESSION_ID)

    def test_empty_dict_returns_empty_list(self) -> None:
        self.assertEqual(mod.build_segments({}), [])


# ============================================================ build_mixed_segment
class BuildMixedSegmentTest(unittest.TestCase):
    def test_builds_single_mix_segment(self) -> None:
        segs = mod.build_mixed_segment("你好")
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0]["speaker"], "mix")
        self.assertEqual(segs[0]["words"], "你 好")

    def test_empty_text_returns_empty_list(self) -> None:
        self.assertEqual(mod.build_mixed_segment(""), [])
        self.assertEqual(mod.build_mixed_segment("   "), [])

    def test_segment_has_session_id(self) -> None:
        segs = mod.build_mixed_segment("商")
        self.assertEqual(segs[0]["session_id"], mod.SESSION_ID)


# ============================================================ safe_cpwer / safe_orcwer
@unittest.skipUnless(HAS_MEETEVAL, "MeetEval not installed")
class SafeCpwerTest(unittest.TestCase):
    def test_empty_ref_returns_sentinel(self) -> None:
        er, errs, length = mod.safe_cpwer([], [{"session_id": "s1", "speaker": "a", "words": "x"}])
        self.assertEqual(er, 1.0)
        self.assertEqual(errs, -1)
        self.assertEqual(length, -1)

    def test_empty_hyp_returns_sentinel(self) -> None:
        er, errs, length = mod.safe_cpwer(
            [{"session_id": "s1", "speaker": "a", "words": "x"}], []
        )
        self.assertEqual(er, 1.0)
        self.assertEqual(errs, -1)

    def test_perfect_match_returns_zero(self) -> None:
        ref = [{"session_id": "s1", "speaker": "a", "words": "你 好"}]
        hyp = [{"session_id": "s1", "speaker": "a", "words": "你 好"}]
        er, errs, length = mod.safe_cpwer(ref, hyp)
        self.assertAlmostEqual(er, 0.0, places=6)
        self.assertEqual(errs, 0)


@unittest.skipUnless(HAS_MEETEVAL, "MeetEval not installed")
class SafeOrcwerTest(unittest.TestCase):
    def test_empty_ref_returns_sentinel(self) -> None:
        er, errs, length = mod.safe_orcwer(
            [], [{"session_id": "s1", "speaker": "mix", "words": "x"}]
        )
        self.assertEqual(er, 1.0)
        self.assertEqual(errs, -1)

    def test_empty_hyp_returns_sentinel(self) -> None:
        er, errs, length = mod.safe_orcwer(
            [{"session_id": "s1", "speaker": "a", "words": "x"}], []
        )
        self.assertEqual(er, 1.0)

    def test_perfect_match_returns_zero(self) -> None:
        ref = [{"session_id": "s1", "speaker": "a", "words": "你 好"}]
        hyp = [{"session_id": "s1", "speaker": "mix", "words": "你 好"}]
        er, errs, length = mod.safe_orcwer(ref, hyp)
        self.assertAlmostEqual(er, 0.0, places=6)


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


# ============================================================ paired_delta
class PairedDeltaTest(unittest.TestCase):
    def test_distribution_shape(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        b = np.array([0.5, 1.5, 2.5, 3.5, 4.5])
        dist = mod.paired_delta_distribution(a, b, n_boot=300, seed=42)
        self.assertEqual(dist.shape, (300,))

    def test_mean_close_to_point_delta(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        b = np.array([0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5])
        dist = mod.paired_delta_distribution(a, b, n_boot=20000, seed=42)
        self.assertAlmostEqual(float(dist.mean()), float(a.mean() - b.mean()), places=1)

    def test_ci_lo_le_hi(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        b = np.array([0.5, 1.5, 2.5, 3.5, 4.5, 5.5])
        lo, hi = mod.paired_delta_ci(a, b, n_boot=1000, seed=42)
        self.assertLessEqual(lo, hi)

    def test_mismatched_shapes_raise(self) -> None:
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.0, 2.0])
        with self.assertRaises(ValueError):
            mod.paired_delta_distribution(a, b, n_boot=100, seed=42)

    def test_deterministic_with_seed(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0])
        b = np.array([0.5, 1.5, 2.5, 3.5])
        d1 = mod.paired_delta_distribution(a, b, n_boot=200, seed=42)
        d2 = mod.paired_delta_distribution(a, b, n_boot=200, seed=42)
        np.testing.assert_array_equal(d1, d2)


# ============================================================ integration test
@unittest.skipUnless(HAS_MEETEVAL, "MeetEval not installed")
class IntegrationTest(unittest.TestCase):
    """Run the full analysis and assert the output JSON is well-formed and
    consistent with RQ31/RQ39 char-level baselines."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.out_json = mod.OUT_JSON
        if not cls.out_json.exists():
            mod.main()
        cls.data = json.loads(cls.out_json.read_text(encoding="utf-8"))

    def test_label_is_experimental_frontier(self) -> None:
        self.assertEqual(self.data["label"], "experimental/frontier")

    def test_n_windows_is_77(self) -> None:
        self.assertEqual(self.data["n_windows"], 77)

    def test_threshold_is_0_38(self) -> None:
        self.assertAlmostEqual(
            self.data["thresholds"]["lang_id_entropy"], 0.38, places=6
        )

    def test_routing_identical_to_0_409(self) -> None:
        chk = self.data["threshold_routing_check"]
        self.assertTrue(chk["routing_identical"])
        self.assertEqual(chk["n_mixed_at_0_38"], chk["n_mixed_at_0_409"])

    def test_decision_counts_match_rq39(self) -> None:
        # RQ39 (threshold 0.409): mixed=38, separated=39.
        dc = self.data["decision_counts"]
        self.assertEqual(dc["mixed"], 38)
        self.assertEqual(dc["separated"], 39)

    def test_char_corrected_matches_rq39(self) -> None:
        # RQ39 char-level corrected_router_cpwer = 0.906097.
        self.assertAlmostEqual(
            self.data["char_level_baselines"]["corrected_router_char"],
            0.906097, places=5,
        )

    def test_char_oracle_matches_rq39(self) -> None:
        # RQ39 char-level oracle = 0.876847.
        self.assertAlmostEqual(
            self.data["char_level_baselines"]["oracle_char"],
            0.876847, places=5,
        )

    def test_char_mixed_matches_rq39(self) -> None:
        # RQ39 char-level always_mixed = 0.910577.
        self.assertAlmostEqual(
            self.data["char_level_baselines"]["always_mixed_char"],
            0.910577, places=5,
        )

    def test_char_bca_ci_matches_rq39(self) -> None:
        # RQ39 char-level BCa CI = [0.873026, 0.931406].
        bca = self.data["char_level_ci_95"]["corrected_router_char_bca"]
        self.assertAlmostEqual(bca[0], 0.873026, places=4)
        self.assertAlmostEqual(bca[1], 0.931406, places=4)

    def test_word_bca_ci_matches_rq39(self) -> None:
        # Word-level BCa CI must reproduce RQ39 [1.012987, 1.097403].
        bca = self.data["word_level_reference"]["bca_ci_95"]
        self.assertAlmostEqual(bca[0], 1.012987, places=4)
        self.assertAlmostEqual(bca[1], 1.097403, places=4)

    def test_h55a_killed_oracle_inside_ci(self) -> None:
        h = self.data["hypothesis_verdicts"]["H55a"]
        self.assertFalse(h["supported"])
        self.assertTrue(h["oracle_inside_ci"])

    def test_h55b_supported_char_width_narrower(self) -> None:
        h = self.data["hypothesis_verdicts"]["H55b"]
        self.assertTrue(h["supported"])
        cmp = self.data["ci_width_comparison"]
        self.assertLess(cmp["char_level_bca_width"], cmp["word_level_bca_width"])

    def test_h55c_supported_corrected_below_mixed(self) -> None:
        h = self.data["hypothesis_verdicts"]["H55c"]
        self.assertTrue(h["supported"])
        self.assertLess(h["corrected_router_char"], h["always_mixed_char"])

    def test_per_window_has_77_rows(self) -> None:
        self.assertEqual(len(self.data["per_window"]), 77)

    def test_per_window_keys_present(self) -> None:
        r = self.data["per_window"][0]
        for k in ("window_id", "lang_id_entropy", "corrected_decision",
                  "char_corrected_cpwer", "char_oracle_cpwer",
                  "char_mixed_cpwer", "char_separated_cpwer"):
            self.assertIn(k, r)


if __name__ == "__main__":
    unittest.main()
