"""Tests for RQ58: corrected router with n-gram KL-divergence detector.

Pin the PURE helpers used by
``results/frontier/kl_corrected_router/kl_corrected_router_analysis.py``:

  * KL detector primitives imported from ``src.llm_semantic_critic`` (RQ34):
    ``char_ngrams``, ``char_distribution``, ``average_distributions``,
    ``kl_divergence``, ``compute_anomaly_score``, ``build_reference_distribution``,
    ``calibrate_threshold_at_specificity``, ``evaluate_at_threshold``,
    ``subgroup_sensitivity``.
  * New RQ58 routing helpers: ``build_kl_reference``, ``compute_kl_scores``,
    ``kl_route_decision``, ``cpwer_for``, ``lang_id_route_decision``.
  * Bootstrap + BCa CI helpers reimplemented from RQ39: ``bootstrap_indices``,
    ``bootstrap_distribution``, ``percentile_ci``, ``_jackknife_means``,
    ``bca_ci``, ``paired_delta_distribution``, ``paired_delta_ci``.

Synthetic data only — no AISHELL-4 file, no MeetEval, no Whisper, no audio, no
LLM. Label: experimental/frontier.
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
    / "kl_corrected_router"
)
sys.path.insert(0, str(SCRIPT_DIR))

from kl_corrected_router_analysis import (  # noqa: E402
    ALWAYS_MIXED_CPWER,
    EPS,
    MODE_S_WINDOW_IDS,
    N_GRAM,
    ORACLE_BEST_CPWER,
    RQ16_CORRECTED_CPWER,
    SEED,
    TARGET_SPECIFICITY,
    _jackknife_means,
    average_distributions,
    bca_ci,
    bootstrap_distribution,
    bootstrap_indices,
    build_kl_reference,
    build_reference_distribution,
    calibrate_threshold_at_specificity,
    char_distribution,
    char_ngrams,
    compute_anomaly_score,
    compute_kl_scores,
    cpwer_for,
    evaluate_at_threshold,
    kl_divergence,
    kl_route_decision,
    lang_id_route_decision,
    paired_delta_ci,
    paired_delta_distribution,
    percentile_ci,
    subgroup_sensitivity,
)


# ======================================================================
# char_ngrams (RQ34 primitive)
# ======================================================================
class TestCharNgrams(unittest.TestCase):
    def test_bigram_count_basic(self) -> None:
        # "abcd" (whitespace stripped) -> ab, bc, cd = 3 bigrams
        grams = char_ngrams("abcd", n=2)
        self.assertEqual(grams, {"ab": 1, "bc": 1, "cd": 1})

    def test_whitespace_stripped(self) -> None:
        grams = char_ngrams("a b c", n=2)
        self.assertEqual(grams, {"ab": 1, "bc": 1})

    def test_repeated_bigram_counted(self) -> None:
        grams = char_ngrams("abab", n=2)
        self.assertEqual(grams, {"ab": 2, "ba": 1})

    def test_short_text_returns_whole_string(self) -> None:
        # len < n: the whole string is one "gram"
        grams = char_ngrams("a", n=2)
        self.assertEqual(grams, {"a": 1})

    def test_empty_text_returns_empty(self) -> None:
        self.assertEqual(char_ngrams("", n=2), {})

    def test_n_equals_2_default_in_module(self) -> None:
        self.assertEqual(N_GRAM, 2)


# ======================================================================
# char_distribution (RQ34 primitive)
# ======================================================================
class TestCharDistribution(unittest.TestCase):
    def test_distribution_sums_to_one(self) -> None:
        dist = char_distribution("aabbcc", n=2)
        self.assertAlmostEqual(sum(dist.values()), 1.0, places=9)

    def test_uniform_distribution_for_repeated_bigrams(self) -> None:
        # "abab" -> ab:2, ba:1 -> ab=2/3, ba=1/3
        dist = char_distribution("abab", n=2)
        self.assertAlmostEqual(dist["ab"], 2.0 / 3.0, places=9)
        self.assertAlmostEqual(dist["ba"], 1.0 / 3.0, places=9)

    def test_empty_text_returns_empty(self) -> None:
        self.assertEqual(char_distribution("", n=2), {})

    def test_vocab_restricted_returns_zeros_for_unseen(self) -> None:
        dist = char_distribution("ab", n=2, vocab={"ab", "cd"})
        self.assertAlmostEqual(dist["ab"], 1.0, places=9)
        self.assertAlmostEqual(dist["cd"], 0.0, places=9)


# ======================================================================
# average_distributions (RQ34 primitive)
# ======================================================================
class TestAverageDistributions(unittest.TestCase):
    def test_average_of_two_uniform(self) -> None:
        d1 = {"a": 1.0}
        d2 = {"b": 1.0}
        avg = average_distributions([d1, d2])
        self.assertAlmostEqual(avg["a"], 0.5, places=9)
        self.assertAlmostEqual(avg["b"], 0.5, places=9)

    def test_average_keys_are_union(self) -> None:
        d1 = {"a": 0.5, "b": 0.5}
        d2 = {"b": 1.0}
        avg = average_distributions([d1, d2])
        self.assertEqual(set(avg.keys()), {"a", "b"})

    def test_empty_list_returns_empty(self) -> None:
        self.assertEqual(average_distributions([]), {})

    def test_average_of_identical_returns_same(self) -> None:
        d = {"a": 0.3, "b": 0.7}
        avg = average_distributions([d, d, d])
        for k in d:
            self.assertAlmostEqual(avg[k], d[k], places=9)


# ======================================================================
# kl_divergence (RQ34 primitive)
# ======================================================================
class TestKlDivergence(unittest.TestCase):
    def test_identical_distributions_zero_kl(self) -> None:
        d = {"a": 0.5, "b": 0.5}
        self.assertAlmostEqual(kl_divergence(d, d), 0.0, places=6)

    def test_kl_nonnegative(self) -> None:
        p = {"a": 0.9, "b": 0.1}
        q = {"a": 0.1, "b": 0.9}
        self.assertGreater(kl_divergence(p, q), 0.0)

    def test_kl_handles_missing_keys_via_smoothing(self) -> None:
        p = {"a": 1.0}
        q = {"b": 1.0}
        # disjoint support -> large KL (no log(0) due to smoothing)
        kl = kl_divergence(p, q)
        self.assertTrue(math.isfinite(kl))
        self.assertGreater(kl, 0.0)

    def test_kl_empty_returns_zero(self) -> None:
        self.assertEqual(kl_divergence({}, {}), 0.0)

    def test_kl_symmetric_only_for_identical(self) -> None:
        # KL is NOT symmetric in general; KL(p||q) != KL(q||p)
        p = {"a": 0.9, "b": 0.1}
        q = {"a": 0.5, "b": 0.5}
        self.assertNotAlmostEqual(kl_divergence(p, q), kl_divergence(q, p), places=6)


# ======================================================================
# compute_anomaly_score (RQ34 primitive)
# ======================================================================
class TestComputeAnomalyScore(unittest.TestCase):
    def test_empty_text_returns_zero(self) -> None:
        ref = {"ab": 0.5, "bc": 0.5}
        self.assertEqual(compute_anomaly_score("", ref, n=2), 0.0)

    def test_empty_ref_returns_zero(self) -> None:
        self.assertEqual(compute_anomaly_score("abc", {}, n=2), 0.0)

    def test_text_matching_ref_has_low_kl(self) -> None:
        ref = char_distribution("ababcbababc", n=2)
        # text drawn from same distribution -> low KL
        score_same = compute_anomaly_score("ababcbab", ref, n=2)
        # text with novel n-grams -> high KL
        score_novel = compute_anomaly_score("xyzxyz", ref, n=2)
        self.assertLess(score_same, score_novel)

    def test_novel_ngrams_increase_score(self) -> None:
        ref = {"ab": 1.0}
        # "abab" only has grams in ref
        s1 = compute_anomaly_score("abab", ref, n=2)
        # "abxy" has a novel gram "xy"
        s2 = compute_anomaly_score("abxy", ref, n=2)
        self.assertGreater(s2, s1)

    def test_score_nonnegative(self) -> None:
        ref = char_distribution("abcdef", n=2)
        score = compute_anomaly_score("abcd", ref, n=2)
        self.assertGreaterEqual(score, 0.0)


# ======================================================================
# build_reference_distribution (RQ34 primitive)
# ======================================================================
class TestBuildReferenceDistribution(unittest.TestCase):
    def test_reference_is_distribution(self) -> None:
        texts = ["abab", "cdcd", "efef"]
        ref = build_reference_distribution(texts, n=2)
        self.assertGreater(len(ref), 0)
        self.assertAlmostEqual(sum(ref.values()), 1.0, places=6)

    def test_reference_skips_empty_texts(self) -> None:
        texts = ["abab", "", "  ", "cdcd"]
        ref = build_reference_distribution(texts, n=2)
        self.assertGreater(len(ref), 0)

    def test_reference_empty_list_returns_empty(self) -> None:
        self.assertEqual(build_reference_distribution([], n=2), {})

    def test_reference_n_equals_2(self) -> None:
        texts = ["abcd"]
        ref = build_reference_distribution(texts, n=2)
        # bigrams of "abcd": ab, bc, cd
        self.assertEqual(set(ref.keys()), {"ab", "bc", "cd"})


# ======================================================================
# calibrate_threshold_at_specificity (RQ34 primitive)
# ======================================================================
class TestCalibrateThreshold(unittest.TestCase):
    def test_perfect_separation_achieves_high_sensitivity(self) -> None:
        # neg all 1, pos all 5 -> threshold ~1, 100% sens at 100% spec
        neg = [1.0] * 10
        pos = [5.0] * 5
        cal = calibrate_threshold_at_specificity(neg, pos, 0.90)
        self.assertLessEqual(cal["specificity"], 1.0)
        self.assertGreaterEqual(cal["specificity"], 0.90)

    def test_specificity_at_least_target(self) -> None:
        neg = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        pos = [2.0, 3.0, 4.0]
        cal = calibrate_threshold_at_specificity(neg, pos, 0.90)
        self.assertGreaterEqual(cal["specificity"], 0.90 - 1e-9)

    def test_max_fp_computed_correctly(self) -> None:
        neg = [0.0] * 40
        cal = calibrate_threshold_at_specificity(neg, None, 0.90)
        # floor((1-0.9)*40 + eps) = floor(4.0000001) = 4
        self.assertEqual(cal["max_fp"], 4)

    def test_empty_neg_returns_inf_threshold(self) -> None:
        cal = calibrate_threshold_at_specificity([], None, 0.90)
        self.assertEqual(cal["threshold"], float("inf"))
        self.assertEqual(cal["specificity"], 1.0)

    def test_threshold_smallest_valid_for_max_sensitivity(self) -> None:
        # With 10 negs all at 0.5, target 0.9 -> max_fp=1.
        # The smallest candidate that keeps fp<=1 should be chosen.
        neg = [0.5] * 10
        pos = [1.0, 2.0]
        cal = calibrate_threshold_at_specificity(neg, pos, 0.90)
        # All negs equal 0.5, so any threshold <= 0.5 flags all 10 (fp=10 > 1).
        # Threshold must be > 0.5 to flag <= 1 neg. The smallest pos candidate
        # above 0.5 is 1.0, which flags 0 negs.
        self.assertGreater(cal["threshold"], 0.5)


# ======================================================================
# evaluate_at_threshold (RQ34 primitive)
# ======================================================================
class TestEvaluateAtThreshold(unittest.TestCase):
    def test_perfect_classifier(self) -> None:
        scores = [0.1, 0.2, 0.8, 0.9]
        labels = [0, 0, 1, 1]
        ev = evaluate_at_threshold(scores, labels, 0.5)
        self.assertEqual(ev["tp"], 2)
        self.assertEqual(ev["fp"], 0)
        self.assertEqual(ev["tn"], 2)
        self.assertEqual(ev["fn"], 0)
        self.assertAlmostEqual(ev["sensitivity"], 1.0)
        self.assertAlmostEqual(ev["specificity"], 1.0)

    def test_all_missed(self) -> None:
        scores = [0.1, 0.2]
        labels = [1, 1]
        ev = evaluate_at_threshold(scores, labels, 0.5)
        self.assertEqual(ev["tp"], 0)
        self.assertEqual(ev["fn"], 2)
        self.assertAlmostEqual(ev["sensitivity"], 0.0)

    def test_precision_computed(self) -> None:
        scores = [0.6, 0.7, 0.8]
        labels = [1, 0, 1]
        ev = evaluate_at_threshold(scores, labels, 0.5)
        self.assertAlmostEqual(ev["precision"], 2.0 / 3.0, places=9)

    def test_threshold_in_result(self) -> None:
        ev = evaluate_at_threshold([0.5], [1], 0.42)
        self.assertAlmostEqual(ev["threshold"], 0.42)


# ======================================================================
# subgroup_sensitivity (RQ34 primitive)
# ======================================================================
class TestSubgroupSensitivity(unittest.TestCase):
    def test_full_subgroup_flagged(self) -> None:
        scores = [0.9, 0.8, 0.1]
        mask = [True, True, False]
        res = subgroup_sensitivity(scores, mask, 0.5)
        self.assertAlmostEqual(res["sensitivity"], 1.0)
        self.assertEqual(res["tp"], 2)
        self.assertEqual(res["n"], 2)

    def test_none_flagged(self) -> None:
        scores = [0.1, 0.2]
        mask = [True, True]
        res = subgroup_sensitivity(scores, mask, 0.5)
        self.assertAlmostEqual(res["sensitivity"], 0.0)
        self.assertEqual(res["tp"], 0)

    def test_empty_subgroup(self) -> None:
        res = subgroup_sensitivity([0.9], [False], 0.5)
        self.assertAlmostEqual(res["sensitivity"], 0.0)
        self.assertEqual(res["n"], 0)

    def test_partial_subgroup(self) -> None:
        scores = [0.9, 0.1, 0.8]
        mask = [True, True, True]
        res = subgroup_sensitivity(scores, mask, 0.5)
        self.assertAlmostEqual(res["sensitivity"], 2.0 / 3.0, places=9)


# ======================================================================
# build_kl_reference (NEW — RQ58)
# ======================================================================
class TestBuildKlReference(unittest.TestCase):
    def test_reference_built_from_non_hallucinated_only(self) -> None:
        labels = [
            {"hallucinated": False, "separated_text": "abab"},
            {"hallucinated": False, "separated_text": "cdcd"},
            {"hallucinated": True, "separated_text": "zzzzzzz"},
        ]
        ref = build_kl_reference(labels, n=2)
        # hallucinated text "zz" bigrams must NOT dominate; ref built from ab,cd only
        self.assertIn("ab", ref)
        self.assertIn("cd", ref)

    def test_reference_uses_n_2(self) -> None:
        labels = [{"hallucinated": False, "separated_text": "abcd"}]
        ref = build_kl_reference(labels, n=2)
        self.assertEqual(set(ref.keys()), {"ab", "bc", "cd"})

    def test_reference_sums_to_one(self) -> None:
        labels = [
            {"hallucinated": False, "separated_text": "abab"},
            {"hallucinated": False, "separated_text": "bcbc"},
        ]
        ref = build_kl_reference(labels, n=2)
        self.assertAlmostEqual(sum(ref.values()), 1.0, places=6)

    def test_empty_non_hallucinated_returns_empty(self) -> None:
        labels = [{"hallucinated": True, "separated_text": "ab"}]
        self.assertEqual(build_kl_reference(labels, n=2), {})


# ======================================================================
# compute_kl_scores (NEW — RQ58, MAX-across-speakers)
# ======================================================================
class TestComputeKlScores(unittest.TestCase):
    def _window(self, speakers: dict) -> dict:
        return {"separated_text_per_speaker": speakers}

    def test_max_across_speakers(self) -> None:
        ref = char_distribution("ababab", n=2)  # {ab, ba}
        # speaker 1 clean (low KL), speaker 2 novel (high KL) -> MAX = high
        w = self._window({"s1": "abab", "s2": "xyzxyz"})
        scores = compute_kl_scores([w], ref, n=2)
        self.assertEqual(len(scores), 1)
        self.assertGreater(scores[0], 0.0)

    def test_empty_speakers_returns_zero(self) -> None:
        ref = {"ab": 1.0}
        w = self._window({"s1": "", "s2": "  "})
        scores = compute_kl_scores([w], ref, n=2)
        self.assertEqual(scores[0], 0.0)

    def test_no_speakers_returns_zero(self) -> None:
        ref = {"ab": 1.0}
        w = self._window({})
        scores = compute_kl_scores([w], ref, n=2)
        self.assertEqual(scores[0], 0.0)

    def test_max_picks_worst_track(self) -> None:
        ref = char_distribution("ababab", n=2)
        w_clean = self._window({"s1": "abab"})
        w_mixed = self._window({"s1": "abab", "s2": "xyzxyz"})
        scores = compute_kl_scores([w_clean, w_mixed], ref, n=2)
        # The mixed window's MAX score should exceed the clean window's
        self.assertGreater(scores[1], scores[0])

    def test_skips_none_speaker_text(self) -> None:
        ref = {"ab": 1.0}
        w = self._window({"s1": None, "s2": "abab"})
        scores = compute_kl_scores([w], ref, n=2)
        # only s2 contributes; should be finite and low
        self.assertTrue(math.isfinite(scores[0]))


# ======================================================================
# kl_route_decision (NEW — RQ58)
# ======================================================================
class TestKlRouteDecision(unittest.TestCase):
    def test_above_threshold_routes_mixed(self) -> None:
        self.assertEqual(kl_route_decision(5.0, 3.0), "mixed")

    def test_below_threshold_routes_separated(self) -> None:
        self.assertEqual(kl_route_decision(2.0, 3.0), "separated")

    def test_equal_threshold_routes_mixed(self) -> None:
        # >= threshold -> mixed (boundary flags)
        self.assertEqual(kl_route_decision(3.0, 3.0), "mixed")

    def test_equal_within_eps_routes_mixed(self) -> None:
        self.assertEqual(kl_route_decision(3.0 - EPS / 2, 3.0), "mixed")

    def test_far_below_routes_separated(self) -> None:
        self.assertEqual(kl_route_decision(0.0, 5.0), "separated")


# ======================================================================
# cpwer_for (NEW — RQ58)
# ======================================================================
class TestCpwerFor(unittest.TestCase):
    def test_mixed_returns_always_mixed(self) -> None:
        w = {"always_mixed_cpwer": 1.5, "always_separated_cpwer": 2.5}
        self.assertEqual(cpwer_for(w, "mixed"), 1.5)

    def test_separated_returns_always_separated(self) -> None:
        w = {"always_mixed_cpwer": 1.5, "always_separated_cpwer": 2.5}
        self.assertEqual(cpwer_for(w, "separated"), 2.5)

    def test_returns_float(self) -> None:
        w = {"always_mixed_cpwer": 1, "always_separated_cpwer": 2}
        self.assertIsInstance(cpwer_for(w, "mixed"), float)
        self.assertIsInstance(cpwer_for(w, "separated"), float)


# ======================================================================
# lang_id_route_decision (NEW — RQ58, RQ16 comparison)
# ======================================================================
class TestLangIdRouteDecision(unittest.TestCase):
    def test_high_entropy_routes_mixed(self) -> None:
        # multilingual text -> high entropy -> mixed
        w = {"separated_text_per_speaker": {"s1": "hello 你好 카메라"}}
        self.assertEqual(lang_id_route_decision(w), "mixed")

    def test_low_entropy_routes_separated(self) -> None:
        # monoscript Chinese -> low entropy -> separated
        w = {"separated_text_per_speaker": {"s1": "你好世界测试"}}
        self.assertEqual(lang_id_route_decision(w), "separated")

    def test_empty_speakers_routes_separated(self) -> None:
        w = {"separated_text_per_speaker": {"s1": ""}}
        self.assertEqual(lang_id_route_decision(w), "separated")


# ======================================================================
# bootstrap_indices (RQ39 framework)
# ======================================================================
class TestBootstrapIndices(unittest.TestCase):
    def test_shape_is_n_boot_by_n(self) -> None:
        idx = bootstrap_indices(n=10, n_boot=200, seed=42)
        self.assertEqual(idx.shape, (200, 10))

    def test_indices_in_range(self) -> None:
        idx = bootstrap_indices(n=7, n_boot=500, seed=1)
        self.assertGreaterEqual(int(idx.min()), 0)
        self.assertLess(int(idx.max()), 7)

    def test_deterministic_with_seed(self) -> None:
        a = bootstrap_indices(n=5, n_boot=100, seed=42)
        b = bootstrap_indices(n=5, n_boot=100, seed=42)
        np.testing.assert_array_equal(a, b)

    def test_different_seeds_usually_differ(self) -> None:
        a = bootstrap_indices(n=20, n_boot=100, seed=1)
        b = bootstrap_indices(n=20, n_boot=100, seed=2)
        self.assertFalse(np.array_equal(a, b))


# ======================================================================
# bootstrap_distribution (RQ39 framework)
# ======================================================================
class TestBootstrapDistribution(unittest.TestCase):
    def test_returns_n_boot_means(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = bootstrap_distribution(values, n_boot=500, seed=42)
        self.assertEqual(dist.shape, (500,))

    def test_mean_of_distribution_close_to_sample_mean(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        dist = bootstrap_distribution(values, n_boot=20000, seed=42)
        self.assertAlmostEqual(float(dist.mean()), float(values.mean()), places=1)

    def test_deterministic_with_seed(self) -> None:
        values = np.array([0.1, 0.5, 0.9, 1.2, 0.3])
        a = bootstrap_distribution(values, n_boot=200, seed=42)
        b = bootstrap_distribution(values, n_boot=200, seed=42)
        np.testing.assert_array_equal(a, b)

    def test_each_mean_within_min_max(self) -> None:
        values = np.array([0.0, 1.0, 2.0, 3.0])
        dist = bootstrap_distribution(values, n_boot=100, seed=7)
        self.assertGreaterEqual(float(dist.min()), 0.0)
        self.assertLessEqual(float(dist.max()), 3.0)


# ======================================================================
# percentile_ci (RQ39 framework)
# ======================================================================
class TestPercentileCI(unittest.TestCase):
    def test_lo_le_hi(self) -> None:
        boot = np.linspace(0.0, 10.0, 1001)
        lo, hi = percentile_ci(boot, alpha=0.05)
        self.assertLessEqual(lo, hi)

    def test_symmetric_distribution_gives_symmetric_ci(self) -> None:
        boot = np.random.default_rng(0).normal(loc=5.0, scale=1.0, size=100000)
        lo, hi = percentile_ci(boot, alpha=0.05)
        self.assertAlmostEqual((lo + hi) / 2.0, 5.0, places=1)
        self.assertAlmostEqual(hi - lo, 2 * 1.96, places=1)

    def test_constant_distribution_returns_constant(self) -> None:
        boot = np.full(500, 3.14)
        lo, hi = percentile_ci(boot, alpha=0.05)
        self.assertAlmostEqual(lo, 3.14)
        self.assertAlmostEqual(hi, 3.14)

    def test_alpha_zero_returns_full_range(self) -> None:
        boot = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        lo, hi = percentile_ci(boot, alpha=0.0)
        self.assertAlmostEqual(lo, 1.0)
        self.assertAlmostEqual(hi, 5.0)


# ======================================================================
# _jackknife_means (RQ39 framework)
# ======================================================================
class TestJackknifeMeans(unittest.TestCase):
    def test_length_matches_input(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0])
        jack = _jackknife_means(values)
        self.assertEqual(len(jack), 4)

    def test_jackknife_mean_correct(self) -> None:
        # leave-one-out mean of [1,2,3,4] leaving out 1 = (2+3+4)/3 = 3
        values = np.array([1.0, 2.0, 3.0, 4.0])
        jack = _jackknife_means(values)
        self.assertAlmostEqual(jack[0], 3.0, places=9)
        # leaving out 4 = (1+2+3)/3 = 2
        self.assertAlmostEqual(jack[3], 2.0, places=9)

    def test_single_element_returns_its_value(self) -> None:
        values = np.array([5.0])
        jack = _jackknife_means(values)
        self.assertEqual(len(jack), 1)
        self.assertAlmostEqual(float(jack[0]), 5.0)

    def test_mean_of_jackknife_close_to_sample_mean(self) -> None:
        values = np.array([2.0, 4.0, 6.0, 8.0, 10.0])
        jack = _jackknife_means(values)
        # E[jackknife mean] = sample mean
        self.assertAlmostEqual(float(jack.mean()), float(values.mean()), places=9)


# ======================================================================
# bca_ci (RQ39 framework)
# ======================================================================
class TestBcaCi(unittest.TestCase):
    def test_lo_le_hi(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        boot = bootstrap_distribution(values, n_boot=2000, seed=42)
        lo, hi = bca_ci(values, boot, alpha=0.05)
        self.assertLessEqual(lo, hi)

    def test_ci_contains_sample_mean(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        boot = bootstrap_distribution(values, n_boot=5000, seed=42)
        lo, hi = bca_ci(values, boot, alpha=0.05)
        sample_mean = float(values.mean())
        self.assertLessEqual(lo, sample_mean)
        self.assertGreaterEqual(hi, sample_mean)

    def test_constant_data_returns_constant(self) -> None:
        values = np.full(10, 2.5)
        boot = bootstrap_distribution(values, n_boot=500, seed=42)
        lo, hi = bca_ci(values, boot, alpha=0.05)
        self.assertAlmostEqual(lo, 2.5, places=6)
        self.assertAlmostEqual(hi, 2.5, places=6)

    def test_single_element_returns_itself(self) -> None:
        values = np.array([7.0])
        boot = bootstrap_distribution(values, n_boot=100, seed=42)
        lo, hi = bca_ci(values, boot, alpha=0.05)
        self.assertAlmostEqual(lo, 7.0)
        self.assertAlmostEqual(hi, 7.0)

    def test_bca_close_to_percentile_for_symmetric_data(self) -> None:
        # For roughly symmetric data, BCa ~ percentile CI
        rng = np.random.default_rng(123)
        values = rng.normal(loc=5.0, scale=1.0, size=200)
        boot = bootstrap_distribution(values, n_boot=5000, seed=42)
        pct_lo, pct_hi = percentile_ci(boot, alpha=0.05)
        bca_lo, bca_hi = bca_ci(values, boot, alpha=0.05)
        self.assertAlmostEqual(bca_lo, pct_lo, places=1)
        self.assertAlmostEqual(bca_hi, pct_hi, places=1)


# ======================================================================
# paired_delta_distribution + paired_delta_ci (RQ39 framework)
# ======================================================================
class TestPairedDelta(unittest.TestCase):
    def test_distribution_shape(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0])
        b = np.array([0.5, 1.5, 2.5, 3.5])
        dist = paired_delta_distribution(a, b, n_boot=300, seed=42)
        self.assertEqual(dist.shape, (300,))

    def test_mean_close_to_difference_of_means(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        b = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        dist = paired_delta_distribution(a, b, n_boot=20000, seed=42)
        self.assertAlmostEqual(float(dist.mean()), float(a.mean() - b.mean()), places=1)

    def test_deterministic_with_seed(self) -> None:
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([0.5, 1.5, 2.5])
        d1 = paired_delta_distribution(a, b, n_boot=200, seed=42)
        d2 = paired_delta_distribution(a, b, n_boot=200, seed=42)
        np.testing.assert_array_equal(d1, d2)

    def test_ci_lo_le_hi(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        b = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
        lo, hi = paired_delta_ci(a, b, n_boot=2000, seed=42)
        self.assertLessEqual(lo, hi)

    def test_mismatched_shapes_raises(self) -> None:
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.0, 2.0])
        with self.assertRaises(ValueError):
            paired_delta_distribution(a, b, n_boot=100, seed=42)

    def test_zero_difference_ci_includes_zero(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        lo, hi = paired_delta_ci(a, a, n_boot=2000, seed=42)
        self.assertLessEqual(lo, 0.0)
        self.assertGreaterEqual(hi, 0.0)


# ======================================================================
# Module constants / config (RQ58 spec)
# ======================================================================
class TestModuleConfig(unittest.TestCase):
    def test_ngram_is_2(self) -> None:
        self.assertEqual(N_GRAM, 2)

    def test_mode_s_windows_are_22_and_30(self) -> None:
        self.assertEqual(MODE_S_WINDOW_IDS, {22, 30})

    def test_target_specificity_is_0_9(self) -> None:
        self.assertAlmostEqual(TARGET_SPECIFICITY, 0.90)

    def test_rq16_reference_cpwer_matches(self) -> None:
        self.assertAlmostEqual(RQ16_CORRECTED_CPWER, 1.04329, places=5)

    def test_oracle_reference_cpwer_matches(self) -> None:
        self.assertAlmostEqual(ORACLE_BEST_CPWER, 1.017316, places=5)

    def test_always_mixed_reference_matches(self) -> None:
        self.assertAlmostEqual(ALWAYS_MIXED_CPWER, 1.17316, places=4)

    def test_seed_is_42(self) -> None:
        self.assertEqual(SEED, 42)


# ======================================================================
# End-to-end routing on synthetic data (integration)
# ======================================================================
class TestEndToEndRouting(unittest.TestCase):
    def _make_windows(self) -> list:
        """Synthetic windows mimicking AISHELL-4 structure."""
        return [
            {  # clean separated -> should route separated
                "window_id": 0,
                "separated_text_per_speaker": {"s1": "你好世界测试一下"},
                "always_mixed_cpwer": 1.0,
                "always_separated_cpwer": 1.0,
            },
            {  # hallucinated diverse -> high KL -> should route mixed
                "window_id": 1,
                "separated_text_per_speaker": {"s1": "xyzqwertyabcdef"},
                "always_mixed_cpwer": 1.0,
                "always_separated_cpwer": 4.0,
            },
            {  # hallucinated mode-s-like -> high KL -> should route mixed
                "window_id": 2,
                "separated_text_per_speaker": {"s1": "zzzzzzzzzzzzzzzzzzzz"},
                "always_mixed_cpwer": 1.0,
                "always_separated_cpwer": 2.0,
            },
        ]

    def test_compute_kl_scores_returns_one_per_window(self) -> None:
        ws = self._make_windows()
        ref = char_distribution("你好世界测试一下你好世界", n=2)
        scores = compute_kl_scores(ws, ref, n=2)
        self.assertEqual(len(scores), len(ws))

    def test_routing_chooses_lower_cpwer_for_hallucinated(self) -> None:
        ws = self._make_windows()
        ref = char_distribution("你好世界测试一下你好世界", n=2)
        scores = compute_kl_scores(ws, ref, n=2)
        # window 1 has separated cpwer 4.0 (bad); if flagged -> mixed (1.0)
        # Use a threshold below window 1's score but above window 0's
        threshold = (scores[0] + scores[1]) / 2.0
        dec1 = kl_route_decision(scores[1], threshold)
        self.assertEqual(dec1, "mixed")
        cpw1 = cpwer_for(ws[1], dec1)
        self.assertEqual(cpw1, 1.0)  # mixed saved the bad separated

    def test_cpwer_for_route_choice(self) -> None:
        ws = self._make_windows()
        self.assertEqual(cpwer_for(ws[1], "mixed"), 1.0)
        self.assertEqual(cpwer_for(ws[1], "separated"), 4.0)

    def test_max_across_speakers_picks_worst_track(self) -> None:
        ref = char_distribution("你好世界测试一下你好世界", n=2)
        w = {"separated_text_per_speaker": {
            "s1": "你好世界",  # clean
            "s2": "xyzqwerty",  # novel -> high KL
        }}
        w_clean = {"separated_text_per_speaker": {"s1": "你好世界"}}
        s_mixed = compute_kl_scores([w], ref, n=2)[0]
        s_clean = compute_kl_scores([w_clean], ref, n=2)[0]
        self.assertGreater(s_mixed, s_clean)

    def test_calibration_then_routing_end_to_end(self) -> None:
        # 6 non-halluc (low KL), 3 halluc (high KL) -> calibrate at 90% spec
        ref = char_distribution("你好世界测试一下你好世界", n=2)
        neg_windows = [
            {"separated_text_per_speaker": {"s1": "你好世界测试"}} for _ in range(6)
        ]
        pos_windows = [
            {"separated_text_per_speaker": {"s1": "xyzqwertyabcdef"}},
            {"separated_text_per_speaker": {"s1": "zzzzzzzzzzzzzzzz"}},
            {"separated_text_per_speaker": {"s1": "qqqqqqqqqqqqqqqq"}},
        ]
        all_windows = neg_windows + pos_windows
        labels = [False] * 6 + [True] * 3
        scores = compute_kl_scores(all_windows, ref, n=2)
        neg_scores = [s for s, l in zip(scores, labels) if not l]
        pos_scores = [s for s, l in zip(scores, labels) if l]
        cal = calibrate_threshold_at_specificity(neg_scores, pos_scores, 0.90)
        # all positives should be flagged
        for s in pos_scores:
            self.assertEqual(kl_route_decision(s, cal["threshold"]), "mixed")
        # specificity should meet target
        self.assertGreaterEqual(cal["specificity"], 0.90 - 1e-9)


if __name__ == "__main__":
    unittest.main()
