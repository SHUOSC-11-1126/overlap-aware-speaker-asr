"""Tests for RQ67: 3-gram KL-divergence detector for Mode S (experimental/frontier).

Pin the PURE helpers used by
``results/frontier/three_gram_kl_detector/analysis.py``: KL detector helpers
(``build_kl_reference``, ``compute_kl_scores``, ``kl_route_decision``,
``cpwer_for``), ROC AUC + ROC curve helpers (``roc_auc``, ``roc_curve``), and
the bootstrap / BCa / paired-delta CI helpers (``bootstrap_indices``,
``bootstrap_distribution``, ``percentile_ci``, ``_jackknife_means``,
``bca_ci``, ``paired_delta_distribution``, ``paired_delta_ci``).

The KL detector primitives themselves (``build_reference_distribution``,
``compute_anomaly_score``, ``calibrate_threshold_at_specificity``,
``evaluate_at_threshold``, ``subgroup_sensitivity``, ``max_across_speakers``,
``label_window``, ``separated_concat``) are imported VERBATIM from
``src.llm_semantic_critic`` (RQ34) — those are covered by RQ34's own tests; we
import them only to build synthetic windows for the end-to-end integration
test.

All tests use SYNTHETIC data only — no AISHELL-4 file, no Whisper, no audio,
no LLM, no ollama. MeetEval is not required (the integration test reads stored
cpWER values, not MeetEval outputs), but the meeteval import is guarded with
``try/except ImportError`` per the harness convention.
"""
from __future__ import annotations

import importlib.util
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
    / "three_gram_kl_detector"
    / "analysis.py"
)
_spec = importlib.util.spec_from_file_location(
    "three_gram_kl_analysis", _MODULE_PATH
)
assert _spec is not None and _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

# MeetEval is not strictly required by this reanalysis (stored cpWER values are
# read, not recomputed), but the import is guarded per the harness convention.
try:  # noqa: SIM105
    import meeteval  # noqa: F401
    HAS_MEETEVAL = True
except ImportError:
    HAS_MEETEVAL = False


# =================================================================== config
class ConfigTest(unittest.TestCase):
    """RQ67 config constants — must match the pre-registered hypothesis spec."""

    def test_ngram_is_3(self) -> None:
        self.assertEqual(mod.N_GRAM, 3)

    def test_ngram_reference_is_2(self) -> None:
        self.assertEqual(mod.N_GRAM_REF, 2)

    def test_rq58_2gram_cpwer_constant(self) -> None:
        self.assertAlmostEqual(mod.RQ58_2GRAM_CPWER, 1.030303, places=6)

    def test_rq58_2gram_threshold_constant(self) -> None:
        self.assertAlmostEqual(mod.RQ58_2GRAM_THRESHOLD, 5.418144, places=6)

    def test_alpha_is_0_05(self) -> None:
        self.assertEqual(mod.ALPHA, 0.05)

    def test_h67c_kill_threshold_is_1_030(self) -> None:
        self.assertAlmostEqual(mod.H67C_KILL_THRESHOLD, 1.030, places=6)

    def test_mode_s_window_ids_are_22_and_30(self) -> None:
        self.assertEqual(mod.MODE_S_WINDOW_IDS, {22, 30})

    def test_always_mixed_cpwer_constant(self) -> None:
        self.assertAlmostEqual(mod.ALWAYS_MIXED_CPWER, 1.17316, places=5)

    def test_always_separated_cpwer_constant(self) -> None:
        self.assertAlmostEqual(mod.ALWAYS_SEPARATED_CPWER, 1.590909, places=5)

    def test_oracle_best_cpwer_constant(self) -> None:
        self.assertAlmostEqual(mod.ORACLE_BEST_CPWER, 1.017316, places=5)


# ============================================================ build_kl_reference
class BuildKLReferenceTest(unittest.TestCase):
    """build_kl_reference: average n-gram distribution of non-hallucinated texts."""

    def test_returns_nonempty_dict_for_clean_chinese(self) -> None:
        labels = [
            {"separated_text": "商场经理这次把大家伙儿叫过来", "hallucinated": False},
            {"separated_text": "我们今天讨论一下这个方案", "hallucinated": False},
        ]
        ref = mod.build_kl_reference(labels, n=3)
        self.assertIsInstance(ref, dict)
        self.assertGreater(len(ref), 0)

    def test_skips_hallucinated_windows(self) -> None:
        clean = "商场经理这次把大家伙儿叫过来"
        labels = [
            {"separated_text": clean, "hallucinated": False},
            {"separated_text": "x", "hallucinated": True},
        ]
        ref = mod.build_kl_reference(labels, n=3)
        # The hallucinated text "x" is too short to form a 3-gram; ref should
        # contain only 3-grams from `clean`.
        for gram in ref:
            self.assertIn(gram, clean.replace(" ", ""))

    def test_3gram_keys_are_length_3_and_2gram_keys_are_length_2(self) -> None:
        labels = [
            {"separated_text": "商场经理这次把大家伙儿叫过来开个会", "hallucinated": False},
            {"separated_text": "我们今天讨论一下这个方案怎么样", "hallucinated": False},
        ]
        ref3 = mod.build_kl_reference(labels, n=3)
        ref2 = mod.build_kl_reference(labels, n=2)
        self.assertGreater(len(ref3), 0)
        self.assertGreater(len(ref2), 0)
        for gram in ref3:
            self.assertEqual(len(gram), 3)
        for gram in ref2:
            self.assertEqual(len(gram), 2)

    def test_returns_empty_for_all_hallucinated(self) -> None:
        labels = [
            {"separated_text": "商场经理", "hallucinated": True},
        ]
        ref = mod.build_kl_reference(labels, n=3)
        self.assertEqual(ref, {})

    def test_skips_empty_separated_text(self) -> None:
        labels = [
            {"separated_text": "", "hallucinated": False},
            {"separated_text": "   ", "hallucinated": False},
            {"separated_text": "商场经理开会", "hallucinated": False},
        ]
        ref = mod.build_kl_reference(labels, n=3)
        self.assertGreater(len(ref), 0)


# ============================================================ compute_kl_scores
class ComputeKLScoresTest(unittest.TestCase):
    """compute_kl_scores: MAX-across-speakers n-gram KL per window."""

    def test_returns_one_score_per_window(self) -> None:
        ref = mod.build_kl_reference(
            [{"separated_text": "商场经理开会讨论方案", "hallucinated": False}], n=3
        )
        windows = [
            {"separated_text_per_speaker": {"a": "商场经理开会"}},
            {"separated_text_per_speaker": {"a": "完全不同的奇怪文本"}},
        ]
        scores = mod.compute_kl_scores(windows, ref, n=3)
        self.assertEqual(len(scores), 2)

    def test_returns_zero_for_window_with_no_speaker_text(self) -> None:
        ref = mod.build_kl_reference(
            [{"separated_text": "商场经理开会", "hallucinated": False}], n=3
        )
        windows = [{"separated_text_per_speaker": {"a": "", "b": "  "}}]
        scores = mod.compute_kl_scores(windows, ref, n=3)
        self.assertEqual(scores, [0.0])

    def test_takes_max_across_speakers(self) -> None:
        ref = mod.build_kl_reference(
            [{"separated_text": "商场经理开会讨论方案", "hallucinated": False}], n=3
        )
        # One clean speaker + one anomalous speaker -> MAX should pick anomalous.
        windows = [{
            "separated_text_per_speaker": {
                "a": "商场经理开会",
                "b": "zzzzqqqqxxxxwwww",  # novel Latin 3-grams -> high KL
            }
        }]
        scores = mod.compute_kl_scores(windows, ref, n=3)
        self.assertGreater(scores[0], 0.0)

    def test_clean_text_has_lower_score_than_novel_text(self) -> None:
        ref = mod.build_kl_reference(
            [{"separated_text": "商场经理开会讨论方案预算", "hallucinated": False}], n=3
        )
        windows = [
            {"separated_text_per_speaker": {"a": "商场经理开会讨论方案"}},
            {"separated_text_per_speaker": {"a": "zzzzqqqqxxxxwwwwjjjj"}},
        ]
        scores = mod.compute_kl_scores(windows, ref, n=3)
        self.assertLess(scores[0], scores[1])

    def test_skips_empty_speakers_in_max(self) -> None:
        ref = mod.build_kl_reference(
            [{"separated_text": "商场经理开会", "hallucinated": False}], n=3
        )
        windows = [{
            "separated_text_per_speaker": {"a": "", "b": "  ", "c": "商场经理"}
        }]
        scores = mod.compute_kl_scores(windows, ref, n=3)
        self.assertEqual(len(scores), 1)
        # Should not raise; the empty speakers are skipped, score from "c" used.
        self.assertGreaterEqual(scores[0], 0.0)


# ============================================================ kl_route_decision
class KLRouteDecisionTest(unittest.TestCase):
    """kl_route_decision: route to MIXED if KL >= threshold, else SEPARATED."""

    def test_high_score_routes_to_mixed(self) -> None:
        self.assertEqual(mod.kl_route_decision(10.0, 5.0), "mixed")

    def test_low_score_routes_to_separated(self) -> None:
        self.assertEqual(mod.kl_route_decision(1.0, 5.0), "separated")

    def test_exact_threshold_routes_to_mixed(self) -> None:
        # >= threshold - eps means the boundary score itself is flagged.
        self.assertEqual(mod.kl_route_decision(5.0, 5.0), "mixed")

    def test_just_below_threshold_routes_to_separated(self) -> None:
        self.assertEqual(mod.kl_route_decision(5.0 - 1e-6, 5.0), "separated")

    def test_within_eps_of_threshold_routes_to_mixed(self) -> None:
        # A score within EPS below the threshold still flags (eps tolerance).
        self.assertEqual(mod.kl_route_decision(5.0 - mod.EPS / 2, 5.0), "mixed")


# ============================================================ cpwer_for
class CpwerForTest(unittest.TestCase):
    """cpwer_for: read the stored word-level cpWER for the chosen route."""

    def test_mixed_returns_always_mixed_cpwer(self) -> None:
        window = {"always_mixed_cpwer": 1.0, "always_separated_cpwer": 2.5}
        self.assertEqual(mod.cpwer_for(window, "mixed"), 1.0)

    def test_separated_returns_always_separated_cpwer(self) -> None:
        window = {"always_mixed_cpwer": 1.0, "always_separated_cpwer": 2.5}
        self.assertEqual(mod.cpwer_for(window, "separated"), 2.5)

    def test_returns_float_type(self) -> None:
        window = {"always_mixed_cpwer": 1, "always_separated_cpwer": 2}
        self.assertIsInstance(mod.cpwer_for(window, "mixed"), float)
        self.assertIsInstance(mod.cpwer_for(window, "separated"), float)

    def test_string_numeric_values_coerced_to_float(self) -> None:
        window = {"always_mixed_cpwer": "1.5", "always_separated_cpwer": "3.0"}
        self.assertAlmostEqual(mod.cpwer_for(window, "mixed"), 1.5)
        self.assertAlmostEqual(mod.cpwer_for(window, "separated"), 3.0)


# ============================================================ roc_auc
class RocAucTest(unittest.TestCase):
    """roc_auc: Mann-Whitney U with average-rank tie handling."""

    def test_perfect_separation_is_1(self) -> None:
        # All positives have higher scores than all negatives.
        scores = [0.1, 0.2, 0.3, 0.8, 0.9, 1.0]
        labels = [0, 0, 0, 1, 1, 1]
        self.assertAlmostEqual(mod.roc_auc(scores, labels), 1.0, places=6)

    def test_perfect_inversion_is_0(self) -> None:
        # All positives have LOWER scores than all negatives -> AUC 0.0.
        scores = [0.1, 0.2, 0.3, 0.8, 0.9, 1.0]
        labels = [1, 1, 1, 0, 0, 0]
        self.assertAlmostEqual(mod.roc_auc(scores, labels), 0.0, places=6)

    def test_random_overlap_is_0_5(self) -> None:
        # Identical score distributions -> AUC 0.5.
        scores = [1, 2, 3, 4, 1, 2, 3, 4]
        labels = [0, 0, 0, 0, 1, 1, 1, 1]
        self.assertAlmostEqual(mod.roc_auc(scores, labels), 0.5, places=6)

    def test_all_ties_is_0_5(self) -> None:
        scores = [5.0, 5.0, 5.0, 5.0]
        labels = [0, 0, 1, 1]
        self.assertAlmostEqual(mod.roc_auc(scores, labels), 0.5, places=6)

    def test_empty_positive_class_returns_0_5(self) -> None:
        scores = [1.0, 2.0, 3.0]
        labels = [0, 0, 0]
        self.assertAlmostEqual(mod.roc_auc(scores, labels), 0.5, places=6)

    def test_empty_negative_class_returns_0_5(self) -> None:
        scores = [1.0, 2.0, 3.0]
        labels = [1, 1, 1]
        self.assertAlmostEqual(mod.roc_auc(scores, labels), 0.5, places=6)

    def test_partial_overlap_between_0_and_1(self) -> None:
        # 1 discordant pair out of 4*4=16 -> AUC = 15/16.
        scores = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        labels = [0, 0, 0, 0, 1, 1, 1, 1]
        # All positives above all negatives -> 1.0; introduce one crossover.
        scores = [0.1, 0.2, 0.3, 0.55, 0.5, 0.6, 0.7, 0.8]
        labels = [0, 0, 0, 0, 1, 1, 1, 1]
        auc = mod.roc_auc(scores, labels)
        self.assertGreater(auc, 0.5)
        self.assertLess(auc, 1.0)

    def test_known_value_two_pos_two_neg(self) -> None:
        # positives: scores 3, 4; negatives: scores 1, 2. AUC = 1.0.
        scores = [1, 2, 3, 4]
        labels = [0, 0, 1, 1]
        self.assertAlmostEqual(mod.roc_auc(scores, labels), 1.0, places=6)


# ============================================================ roc_curve
class RocCurveTest(unittest.TestCase):
    """roc_curve: FPR/TPR curve + AUC + shape summary."""

    def test_curve_starts_at_0_0(self) -> None:
        scores = [0.1, 0.2, 0.8, 0.9]
        labels = [0, 0, 1, 1]
        roc = mod.roc_curve(scores, labels)
        self.assertEqual(roc["fpr"][0], 0.0)
        self.assertEqual(roc["tpr"][0], 0.0)

    def test_curve_ends_at_1_1(self) -> None:
        scores = [0.1, 0.2, 0.8, 0.9]
        labels = [0, 0, 1, 1]
        roc = mod.roc_curve(scores, labels)
        self.assertEqual(roc["fpr"][-1], 1.0)
        self.assertEqual(roc["tpr"][-1], 1.0)

    def test_auc_in_curve_matches_roc_auc(self) -> None:
        scores = [0.1, 0.2, 0.8, 0.9]
        labels = [0, 0, 1, 1]
        roc = mod.roc_curve(scores, labels)
        self.assertAlmostEqual(roc["auc"], mod.roc_auc(scores, labels), places=6)

    def test_perfect_separation_max_sens_at_90_spec_is_1(self) -> None:
        scores = [0.1, 0.2, 0.3, 0.4, 0.8, 0.9, 1.0, 1.1]
        labels = [0, 0, 0, 0, 1, 1, 1, 1]
        roc = mod.roc_curve(scores, labels)
        self.assertAlmostEqual(roc["max_sens_at_90pct_spec"], 1.0, places=6)
        self.assertFalse(roc["plateau_below_1_at_90pct_spec"])

    def test_plateau_detected_when_sens_cannot_reach_1(self) -> None:
        # Construct a case where at >=90% specificity, sensitivity < 1.
        # 10 negatives at 0.0; 1 negative at 5.0; 1 positive at 5.0; rest at 10.
        # 90% specificity on 11 negatives -> max_fp = floor(0.1*11) = 1.
        # At threshold 5.0, fp=1 (the 5.0 neg), tp=1 (the 5.0 pos); the 10.0 pos
        # is also flagged. Actually need a case where one positive is BELOW the
        # 90%-spec threshold. Simpler: 1 neg at score 0, 1 neg at score 5,
        # 1 pos at score 1 (below the 5), 1 pos at score 10. At 90% spec on 2
        # negs -> max_fp = floor(0.1*2) = 0 -> must flag 0 negs -> threshold
        # above 5 -> only the score-10 pos flagged -> sens 1/2 -> plateau.
        scores = [0.0, 5.0, 1.0, 10.0]
        labels = [0, 0, 1, 1]
        roc = mod.roc_curve(scores, labels)
        self.assertLess(roc["max_sens_at_90pct_spec"], 1.0)
        self.assertTrue(roc["plateau_below_1_at_90pct_spec"])

    def test_empty_positive_class_returns_default(self) -> None:
        scores = [1.0, 2.0]
        labels = [0, 0]
        roc = mod.roc_curve(scores, labels)
        self.assertEqual(roc["auc"], 0.5)
        self.assertEqual(roc["fpr"], [])
        self.assertFalse(roc["plateau_below_1_at_90pct_spec"])

    def test_empty_negative_class_returns_default(self) -> None:
        scores = [1.0, 2.0]
        labels = [1, 1]
        roc = mod.roc_curve(scores, labels)
        self.assertEqual(roc["auc"], 0.5)
        self.assertFalse(roc["plateau_below_1_at_90pct_spec"])

    def test_first_threshold_is_none_representing_inf(self) -> None:
        scores = [0.1, 0.2, 0.8, 0.9]
        labels = [0, 0, 1, 1]
        roc = mod.roc_curve(scores, labels)
        # The +inf threshold (nothing flagged) is serialised as None.
        self.assertIsNone(roc["thresholds"][0])

    def test_thresholds_are_descending(self) -> None:
        scores = [0.1, 0.2, 0.8, 0.9]
        labels = [0, 0, 1, 1]
        roc = mod.roc_curve(scores, labels)
        finite = [t for t in roc["thresholds"] if t is not None]
        for a, b in zip(finite, finite[1:]):
            self.assertGreaterEqual(a, b)


# ============================================================ bootstrap_indices
class BootstrapIndicesTest(unittest.TestCase):
    """bootstrap_indices: deterministic (n_boot, n) resample index array."""

    def test_shape_is_n_boot_by_n(self) -> None:
        idx = mod.bootstrap_indices(10, 50, seed=42)
        self.assertEqual(idx.shape, (50, 10))

    def test_indices_in_range_0_to_n_minus_1(self) -> None:
        idx = mod.bootstrap_indices(10, 50, seed=42)
        self.assertGreaterEqual(int(idx.min()), 0)
        self.assertLess(int(idx.max()), 10)

    def test_deterministic_for_fixed_seed(self) -> None:
        a = mod.bootstrap_indices(10, 50, seed=42)
        b = mod.bootstrap_indices(10, 50, seed=42)
        np.testing.assert_array_equal(a, b)

    def test_different_seeds_give_different_indices(self) -> None:
        a = mod.bootstrap_indices(10, 50, seed=42)
        b = mod.bootstrap_indices(10, 50, seed=43)
        self.assertFalse(np.array_equal(a, b))


# ============================================================ bootstrap_distribution
class BootstrapDistributionTest(unittest.TestCase):
    """bootstrap_distribution: n_boot means of resampled values."""

    def test_returns_n_boot_means(self) -> None:
        values = np.arange(100, dtype=float)
        dist = mod.bootstrap_distribution(values, 1000, seed=42)
        self.assertEqual(len(dist), 1000)

    def test_mean_of_distribution_close_to_sample_mean(self) -> None:
        rng = np.random.default_rng(0)
        values = rng.normal(5.0, 1.0, size=500)
        dist = mod.bootstrap_distribution(values, 5000, seed=42)
        self.assertAlmostEqual(float(dist.mean()), float(values.mean()), places=1)

    def test_deterministic_for_fixed_seed(self) -> None:
        values = np.arange(100, dtype=float)
        a = mod.bootstrap_distribution(values, 100, seed=42)
        b = mod.bootstrap_distribution(values, 100, seed=42)
        np.testing.assert_array_equal(a, b)


# ============================================================ percentile_ci
class PercentileCiTest(unittest.TestCase):
    """percentile_ci: (lo, hi) percentile bounds of the bootstrap distribution."""

    def test_lo_lt_hi(self) -> None:
        rng = np.random.default_rng(0)
        dist = rng.normal(0, 1, size=10000)
        lo, hi = mod.percentile_ci(dist)
        self.assertLess(lo, hi)

    def test_lo_is_2_5_percentile(self) -> None:
        dist = np.arange(1, 10001, dtype=float)  # 1..10000
        lo, hi = mod.percentile_ci(dist)
        self.assertAlmostEqual(lo, np.percentile(dist, 2.5), places=6)
        self.assertAlmostEqual(hi, np.percentile(dist, 97.5), places=6)

    def test_alpha_0_1_gives_5_95_bounds(self) -> None:
        dist = np.arange(1, 10001, dtype=float)
        lo, hi = mod.percentile_ci(dist, alpha=0.1)
        self.assertAlmostEqual(lo, np.percentile(dist, 5.0), places=6)
        self.assertAlmostEqual(hi, np.percentile(dist, 95.0), places=6)


# ============================================================ _jackknife_means
class JackknifeMeansTest(unittest.TestCase):
    """_jackknife_means: leave-one-out means via the O(n) identity."""

    def test_length_matches_input(self) -> None:
        values = np.arange(10, dtype=float)
        jack = mod._jackknife_means(values)
        self.assertEqual(len(jack), 10)

    def test_matches_brute_force_leave_one_out(self) -> None:
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        jack = mod._jackknife_means(values)
        brute = np.array([np.delete(values, i).mean() for i in range(len(values))])
        np.testing.assert_allclose(jack, brute)

    def test_single_element_returns_its_own_mean(self) -> None:
        values = np.array([7.0])
        jack = mod._jackknife_means(values)
        self.assertEqual(len(jack), 1)
        self.assertAlmostEqual(float(jack[0]), 7.0)

    def test_constant_array_returns_constant(self) -> None:
        values = np.array([3.0, 3.0, 3.0, 3.0])
        jack = mod._jackknife_means(values)
        np.testing.assert_allclose(jack, np.full(4, 3.0))


# ============================================================ bca_ci
class BcaCiTest(unittest.TestCase):
    """bca_ci: bias-corrected + accelerated bootstrap CI for the mean."""

    def test_lo_lt_hi_for_normal_data(self) -> None:
        rng = np.random.default_rng(0)
        values = rng.normal(0, 1, size=200)
        boot = mod.bootstrap_distribution(values, 5000, seed=42)
        lo, hi = mod.bca_ci(values, boot)
        self.assertLess(lo, hi)

    def test_ci_brackets_sample_mean(self) -> None:
        rng = np.random.default_rng(0)
        values = rng.normal(5.0, 1.0, size=500)
        boot = mod.bootstrap_distribution(values, 5000, seed=42)
        lo, hi = mod.bca_ci(values, boot)
        mean = float(values.mean())
        self.assertLessEqual(lo, mean)
        self.assertLessEqual(mean, hi)

    def test_single_element_returns_that_element(self) -> None:
        values = np.array([7.0])
        boot = mod.bootstrap_distribution(values, 100, seed=42)
        lo, hi = mod.bca_ci(values, boot)
        self.assertAlmostEqual(lo, 7.0)
        self.assertAlmostEqual(hi, 7.0)

    def test_constant_array_returns_constant(self) -> None:
        # Constant array -> zero acceleration; BCa reduces to percentile CI.
        values = np.full(50, 3.0)
        boot = mod.bootstrap_distribution(values, 1000, seed=42)
        lo, hi = mod.bca_ci(values, boot)
        self.assertAlmostEqual(lo, 3.0, places=6)
        self.assertAlmostEqual(hi, 3.0, places=6)


# ============================================================ paired_delta_distribution
class PairedDeltaDistributionTest(unittest.TestCase):
    """paired_delta_distribution: bootstrap mean(a[idx]) - mean(b[idx])."""

    def test_returns_n_boot_deltas(self) -> None:
        a = np.arange(50, dtype=float)
        b = np.arange(50, dtype=float) + 1.0
        dist = mod.paired_delta_distribution(a, b, 1000, seed=42)
        self.assertEqual(len(dist), 1000)

    def test_mean_delta_close_to_mean_a_minus_mean_b(self) -> None:
        a = np.arange(100, dtype=float)
        b = np.arange(100, dtype=float) + 2.0
        dist = mod.paired_delta_distribution(a, b, 5000, seed=42)
        self.assertAlmostEqual(float(dist.mean()), -2.0, places=1)

    def test_identical_arrays_give_zero_delta(self) -> None:
        a = np.arange(50, dtype=float)
        dist = mod.paired_delta_distribution(a, a, 1000, seed=42)
        np.testing.assert_allclose(dist, np.zeros(1000))

    def test_shape_mismatch_raises(self) -> None:
        a = np.arange(10, dtype=float)
        b = np.arange(20, dtype=float)
        with self.assertRaises(ValueError):
            mod.paired_delta_distribution(a, b, 100, seed=42)


# ============================================================ paired_delta_ci
class PairedDeltaCiTest(unittest.TestCase):
    """paired_delta_ci: percentile CI for the paired bootstrap delta."""

    def test_lo_lt_hi(self) -> None:
        rng = np.random.default_rng(0)
        a = rng.normal(0, 1, size=200)
        b = rng.normal(1, 1, size=200)
        lo, hi = mod.paired_delta_ci(a, b, 5000, seed=42)
        self.assertLess(lo, hi)

    def test_identical_arrays_give_zero_ci(self) -> None:
        a = np.arange(50, dtype=float)
        lo, hi = mod.paired_delta_ci(a, a, 1000, seed=42)
        self.assertAlmostEqual(lo, 0.0, places=6)
        self.assertAlmostEqual(hi, 0.0, places=6)


# ============================================================ integration
class IntegrationTest(unittest.TestCase):
    """End-to-end integration on SYNTHETIC windows: the 3-gram detector's
    cross-class rank equivalence to the 2-gram (the RQ67 headline finding)."""

    @staticmethod
    def _make_synthetic_windows() -> tuple[list, list, dict, dict]:
        """Build 12 synthetic windows: 6 hallucinated (high KL), 6 clean (low KL).

        Each window has per-speaker separated text + the stored cpWER fields the
        corrected router reads. The hallucinated windows use novel character
        3-grams (Latin) so their KL is high; the clean windows use only the
        reference's Chinese 3-grams so their KL is low. Returns
        (windows, labels, ref3, ref2)."""
        clean_texts = [
            "商场经理这次把大家伙儿叫过来开个会",
            "我们今天讨论一下这个方案的可行性",
            "关于预算问题大家有什么看法呢",
            "下个星期我们要提交一份报告",
            "这个问题需要进一步研究才能决定",
            "请大家注意一下会议的时间安排",
        ]
        # Hallucinated: pure Latin strings -> entirely novel 3-grams vs Chinese ref.
        halluc_texts = [
            "zzzqqqxxxwwwvaaabbbccc",
            "mmmnnnppprrrssstttuuu",
            "aaabbbcccdddeeefffggg",
            "hh jj kk ll mm nn oo pp",
            "qqr sst uuv wwx yyz zza",
            "bbbcccdddeeefffgggghhh",
        ]
        windows: list[dict] = []
        labels: list[dict] = []
        for i, txt in enumerate(clean_texts):
            # Clean windows: separated is bad (high cpWER) -> hallucinated=False
            # requires always_separated_cpwer <= 1.0; set 0.9 (non-halluc).
            w = {
                "window_id": i,
                "separated_text_per_speaker": {"a": txt},
                "always_mixed_cpwer": 1.0,
                "always_separated_cpwer": 0.9,
                "router_v2_cpwer": 1.0,
                "oracle_best_cpwer": 0.9,
            }
            windows.append(w)
            labels.append({"separated_text": txt, "hallucinated": False})
        for i, txt in enumerate(halluc_texts):
            # Hallucinated windows: separated is catastrophic -> hallucinated=True.
            w = {
                "window_id": i + 6,
                "separated_text_per_speaker": {"a": txt},
                "always_mixed_cpwer": 1.0,
                "always_separated_cpwer": 2.0,
                "router_v2_cpwer": 2.0,
                "oracle_best_cpwer": 1.0,
            }
            windows.append(w)
            labels.append({"separated_text": txt, "hallucinated": True})
        ref3 = mod.build_kl_reference(labels, n=3)
        ref2 = mod.build_kl_reference(labels, n=2)
        return windows, labels, ref3, ref2

    def test_3gram_and_2gram_both_perfectly_separate_classes(self) -> None:
        windows, labels, ref3, ref2 = self._make_synthetic_windows()
        scores3 = mod.compute_kl_scores(windows, ref3, n=3)
        scores2 = mod.compute_kl_scores(windows, ref2, n=2)
        label_ints = [1 if l["hallucinated"] else 0 for l in labels]
        auc3 = mod.roc_auc(scores3, label_ints)
        auc2 = mod.roc_auc(scores2, label_ints)
        self.assertAlmostEqual(auc3, 1.0, places=6)
        self.assertAlmostEqual(auc2, 1.0, places=6)

    def test_corrected_router_flags_all_hallucinated_windows(self) -> None:
        windows, labels, ref3, _ = self._make_synthetic_windows()
        scores3 = mod.compute_kl_scores(windows, ref3, n=3)
        neg = [s for s, l in zip(scores3, labels) if not l["hallucinated"]]
        pos = [s for s, l in zip(scores3, labels) if l["hallucinated"]]
        cal = mod.calibrate_threshold_at_specificity(neg, pos, 0.90)
        # Every hallucinated window should be flagged at the calibrated threshold.
        for s in pos:
            self.assertEqual(mod.kl_route_decision(s, cal["threshold"]), "mixed")

    def test_corrected_router_cpwer_beats_always_separated(self) -> None:
        windows, labels, ref3, _ = self._make_synthetic_windows()
        scores3 = mod.compute_kl_scores(windows, ref3, n=3)
        neg = [s for s, l in zip(scores3, labels) if not l["hallucinated"]]
        pos = [s for s, l in zip(scores3, labels) if l["hallucinated"]]
        cal = mod.calibrate_threshold_at_specificity(neg, pos, 0.90)
        routed_cpwer = np.array([
            mod.cpwer_for(w, mod.kl_route_decision(s, cal["threshold"]))
            for w, s in zip(windows, scores3)
        ])
        always_sep = np.array([mod.cpwer_for(w, "separated") for w in windows])
        self.assertLess(float(routed_cpwer.mean()), float(always_sep.mean()))

    def test_paired_delta_zero_when_3gram_equals_2gram_decisions(self) -> None:
        # If both detectors make the same routing decisions, the paired delta
        # distribution of the per-window cpWER arrays is exactly zero.
        windows, labels, ref3, ref2 = self._make_synthetic_windows()
        scores3 = mod.compute_kl_scores(windows, ref3, n=3)
        scores2 = mod.compute_kl_scores(windows, ref2, n=2)
        neg3 = [s for s, l in zip(scores3, labels) if not l["hallucinated"]]
        pos3 = [s for s, l in zip(scores3, labels) if l["hallucinated"]]
        neg2 = [s for s, l in zip(scores2, labels) if not l["hallucinated"]]
        pos2 = [s for s, l in zip(scores2, labels) if l["hallucinated"]]
        cal3 = mod.calibrate_threshold_at_specificity(neg3, pos3, 0.90)
        cal2 = mod.calibrate_threshold_at_specificity(neg2, pos2, 0.90)
        cp3 = np.array([
            mod.cpwer_for(w, mod.kl_route_decision(s, cal3["threshold"]))
            for w, s in zip(windows, scores3)
        ])
        cp2 = np.array([
            mod.cpwer_for(w, mod.kl_route_decision(s, cal2["threshold"]))
            for w, s in zip(windows, scores2)
        ])
        # Both detectors perfectly separate -> same decisions -> identical cpWER.
        np.testing.assert_array_equal(cp3, cp2)
        dist = mod.paired_delta_distribution(cp3, cp2, 500, seed=42)
        np.testing.assert_allclose(dist, np.zeros(500))

    def test_h67c_kill_logic_when_cpwer_equals_rq58(self) -> None:
        # The H67c kill criterion is cpWER >= 1.030. When 3-gram cpWER equals
        # RQ58's 1.030303, H67c is killed (supported=False).
        kl3_point = mod.RQ58_2GRAM_CPWER  # equal to RQ58
        h67c_supported = kl3_point < mod.H67C_KILL_THRESHOLD
        self.assertFalse(h67c_supported)

    def test_h67a_kill_logic_when_auc_delta_is_zero(self) -> None:
        # The H67a kill criterion is 3-gram AUC <= 2-gram AUC. When equal, killed.
        auc3 = 0.951351
        auc2 = 0.951351
        self.assertFalse(auc3 > auc2)

    def test_h67b_supported_logic_when_mode_s_sens_is_1(self) -> None:
        # H67b is supported when Mode S sensitivity is 100% (2/2).
        ms_sensitivity = 1.0
        n_mode_s = 2
        self.assertTrue(ms_sensitivity >= 1.0 and n_mode_s == len(mod.MODE_S_WINDOW_IDS))


# ============================================================ results json sanity
class ResultsJsonSanityTest(unittest.TestCase):
    """Sanity-check the committed JSON results file matches the pre-registered
    hypothesis verdicts reported in FINDINGS.md. Read-only — does not modify."""

    @classmethod
    def setUpClass(cls) -> None:
        import json
        cls._json_path = (
            _PROJECT_ROOT
            / "results"
            / "frontier"
            / "three_gram_kl_detector"
            / "three_gram_kl_results.json"
        )

    def test_results_json_exists(self) -> None:
        self.assertTrue(self._json_path.exists())

    def test_results_json_label_is_experimental_frontier(self) -> None:
        import json
        data = json.loads(self._json_path.read_text(encoding="utf-8"))
        self.assertEqual(data["label"], "experimental/frontier")

    def test_results_json_closes_995(self) -> None:
        import json
        data = json.loads(self._json_path.read_text(encoding="utf-8"))
        self.assertEqual(data["closes_issue"], 995)

    def test_h67a_killed_in_committed_json(self) -> None:
        import json
        data = json.loads(self._json_path.read_text(encoding="utf-8"))
        self.assertFalse(data["hypothesis_verdicts"]["H67a"]["supported"])
        self.assertTrue(data["hypothesis_verdicts"]["H67a"]["killed_if_le"])

    def test_h67b_supported_in_committed_json(self) -> None:
        import json
        data = json.loads(self._json_path.read_text(encoding="utf-8"))
        self.assertTrue(data["hypothesis_verdicts"]["H67b"]["supported"])
        self.assertEqual(data["hypothesis_verdicts"]["H67b"]["mode_s_sensitivity"], 1.0)

    def test_h67c_killed_in_committed_json(self) -> None:
        import json
        data = json.loads(self._json_path.read_text(encoding="utf-8"))
        self.assertFalse(data["hypothesis_verdicts"]["H67c"]["supported"])
        self.assertTrue(data["hypothesis_verdicts"]["H67c"]["killed_if_ge_1_030"])

    def test_3gram_cpwer_matches_rq58_in_committed_json(self) -> None:
        import json
        data = json.loads(self._json_path.read_text(encoding="utf-8"))
        self.assertAlmostEqual(
            data["three_gram_corrected_router_cpwer"],
            data["two_gram_recomputed_router_cpwer"],
            places=6,
        )

    def test_3gram_auc_equals_2gram_auc_in_committed_json(self) -> None:
        import json
        data = json.loads(self._json_path.read_text(encoding="utf-8"))
        self.assertAlmostEqual(
            data["roc_analysis"]["auc_n3"],
            data["roc_analysis"]["auc_n2"],
            places=6,
        )

    def test_decision_counts_match_between_3gram_and_2gram(self) -> None:
        import json
        data = json.loads(self._json_path.read_text(encoding="utf-8"))
        c3 = data["three_gram_corrected_router_decision_counts"]
        c2 = data["two_gram_recomputed_router_decision_counts"]
        self.assertEqual(c3, c2)
        self.assertEqual(c3["mixed"] + c3["separated"], 77)

    def test_mode_s_windows_flagged_in_committed_json(self) -> None:
        import json
        data = json.loads(self._json_path.read_text(encoding="utf-8"))
        for wid in ("22", "30"):
            self.assertEqual(data["mode_s_detail"][wid]["kl3_flag"], 1)
            self.assertEqual(data["mode_s_detail"][wid]["kl3_decision"], "mixed")


if __name__ == "__main__":
    unittest.main()
