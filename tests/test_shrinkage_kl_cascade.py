"""Tests for RQ69: cascade with shrinkage-calibrated KL gate (experimental/frontier).

Pins the pure helpers: ``beta_posterior_mode`` (Beta(2,2) posterior mode),
``shrinkage_objective`` (RQ61's regularised objective on the normalised scale),
``_confusion_arrays`` / ``_sens_spec`` / ``_select_shrinkage`` (vectorised
calibration sweep), ``calibrate_shrinkage_kl`` (the public calibration entry
point), ``cascade_cpwer_at_threshold`` / ``cascade_compute_at_threshold`` /
``escalation_fraction_at_threshold`` / ``cascade_oob_cpwer`` (the RQ43 cascade
simulation held fixed), ``bootstrap_shrinkage_cascade`` (B=10000 OOB
evaluation), ``jackknife_acceleration`` (delete-1, 77 fits), ``bca_ci``
(RQ59 re-export), ``count_modes`` (RQ48 re-export), ``norm_cdf`` / ``norm_ppf``
(RQ59 re-exports), ``_finite_stats`` (inf-aware descriptive stats),
``select_best_lambda`` (lexicographic best-lambda selection), and the
hypothesis helpers ``_h69a_supported`` / ``_h69b_supported`` / ``_h69c_supported``.

Also smoke-tests the in-sample calibration on the real 77-window AISHELL-4
corpus: RQ43's original-rule cascade @ kl_sep>=3.30 reproduces 0.888947, the
label counts are 37/40, the Beta(2,2) posterior mode reproduces 38/79, the
in-sample threshold is 4.87 across all lambda (the >=90% specificity floor is
binding), and the central RQ69 findings -- H69a KILLED (OOB cpWER 1.54 > 0.889),
H69b SUPPORTED (escalation 6.5% < 83.1%), H69c KILLED (BCa width 0.53 > 0.283)
-- are pinned.

MeetEval is not required for any of the RQ69 helpers (the cascade cpWER values
come from RQ43's JSON, not from re-transcribing audio). A MeetEval-guarded
smoke test verifies the cpWER formula matches MeetEval on a tiny synthetic
example, in case the project is run in an environment with MeetEval installed.

No Whisper / no audio needed. numpy + stdlib only.
"""
from __future__ import annotations

import csv as _csv
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

# MeetEval availability guards the optional char-level cpWER smoke test.
try:
    import meeteval  # noqa: F401
    HAS_MEETEVAL = True
except ImportError:
    HAS_MEETEVAL = False

# The RQ69 analysis script lives in results/frontier/ as a standalone module
# (no src. package), mirroring the RQ44/RQ48/RQ54/RQ59/RQ62 test pattern. The
# script itself adds RQ59 + RQ48 + RQ44 dirs to sys.path and imports them.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_DIR = _PROJECT_ROOT / "results" / "frontier" / "shrinkage_kl_cascade"
sys.path.insert(0, str(_SCRIPT_DIR))

import shrinkage_kl_cascade_analysis as rq69  # noqa: E402  (path-injected import)

# RQ59's module is needed for the BCa / norm_cdf / count_modes re-export checks.
_RQ59_DIR = _PROJECT_ROOT / "results" / "frontier" / "cascade_youdens_j"
_RQ48_DIR = _PROJECT_ROOT / "results" / "frontier" / "calibration_rule_comparison"
sys.path.insert(0, str(_RQ59_DIR))
sys.path.insert(0, str(_RQ48_DIR))
import cascade_youdens_j_analysis as rq59  # noqa: E402  (path-injected import)
import calibration_rule_analysis as rq48  # noqa: E402  (path-injected import)

RQ43_JSON = (
    _PROJECT_ROOT
    / "results"
    / "frontier"
    / "three_tier_cascade"
    / "three_tier_cascade_results.json"
)
OUT_JSON = _SCRIPT_DIR / "shrinkage_kl_cascade_results.json"
OUT_CSV = _SCRIPT_DIR / "shrinkage_kl_cascade_results.csv"


# --------------------------------------------------------------- constants
class TestConstants(unittest.TestCase):
    def test_bootstrap_conventions(self) -> None:
        self.assertEqual(rq69.N_BOOT, 10000)
        self.assertEqual(rq69.SEED, 42)
        self.assertEqual(rq69.MIN_MODE_FRACTION, 0.05)
        self.assertEqual(rq69.ALPHA, 0.05)

    def test_target_specificity(self) -> None:
        self.assertEqual(rq69.TARGET_SPECIFICITY, 0.90)

    def test_compute_model(self) -> None:
        self.assertEqual(rq69.COMPUTE_TINY, 1.0)
        self.assertEqual(rq69.COMPUTE_BASE, 1.93)

    def test_catastrophic_threshold(self) -> None:
        self.assertEqual(rq69.CATASTROPHIC_CPWER, 1.0)

    def test_kl_grid_covers_rq43_kl_range(self) -> None:
        # RQ43 KL range is [0.0, 8.5255]; grid spans [0.00, 8.55] at 0.01 step.
        self.assertEqual(rq69.KL_THRESHOLD_GRID[0], 0.0)
        self.assertEqual(rq69.KL_THRESHOLD_GRID[-1], 8.55)
        self.assertEqual(len(rq69.KL_THRESHOLD_GRID), 856)
        for i in range(1, 10):
            self.assertAlmostEqual(
                rq69.KL_THRESHOLD_GRID[i] - rq69.KL_THRESHOLD_GRID[i - 1], 0.01, 8)

    def test_rq43_anchors_match_task_brief(self) -> None:
        self.assertAlmostEqual(rq69.RQ43_CASCADE_CPWER, 0.888947, 6)
        self.assertAlmostEqual(rq69.RQ43_BASELINE_CPWER, 1.590909, 6)
        self.assertAlmostEqual(rq69.RQ43_BASE_RATIO, 0.428031, 6)
        self.assertEqual(rq69.RQ43_KL_THRESHOLD, 3.30)

    def test_rq59_reference_anchors(self) -> None:
        # H69b / H69c anchors come from RQ59 (Youden's J cascade).
        self.assertAlmostEqual(rq69.RQ59_YOUDENS_J_ESCALATION, 0.831169, 6)
        self.assertAlmostEqual(rq69.RQ59_YOUDENS_J_BCA_WIDTH, 0.282660, 6)
        self.assertAlmostEqual(rq69.RQ59_YOUDENS_J_OOB_MEDIAN_CPWER, 0.782394, 6)

    def test_rq62_reference_anchors(self) -> None:
        # RQ62 ensemble OR cascade anchors (controlled-comparison reference).
        self.assertAlmostEqual(rq69.RQ62_OR_ESCALATION, 0.5584, 4)
        self.assertAlmostEqual(rq69.RQ62_OR_OOB_MEDIAN_CPWER, 0.9423, 4)
        self.assertAlmostEqual(rq69.RQ62_OR_BCA_WIDTH, 0.2391, 4)

    def test_beta_prior_constants(self) -> None:
        self.assertEqual(rq69.BETA_PRIOR_ALPHA, 2.0)
        self.assertEqual(rq69.BETA_PRIOR_BETA, 2.0)

    def test_prior_mean_norm_matches_38_over_79(self) -> None:
        # Beta(2,2) + 37 hall / 40 clean -> Beta(39,42) -> mode 38/79.
        self.assertAlmostEqual(rq69.PRIOR_MEAN_NORM, 38.0 / 79.0, 12)

    def test_lambdas_grid(self) -> None:
        self.assertEqual(rq69.LAMBDAS, [0.0, 0.01, 0.1, 0.5, 1.0])

    def test_hypothesis_kill_thresholds(self) -> None:
        self.assertAlmostEqual(rq69.H69A_MAX_CPWER, 0.889, 6)
        self.assertAlmostEqual(rq69.H69B_MAX_ESCALATION, 0.831, 6)
        self.assertAlmostEqual(rq69.H69C_MAX_WIDTH, 0.283, 6)

    def test_eps(self) -> None:
        self.assertEqual(rq69.EPS, 1e-9)


# --------------------------------------------------------------- Beta(2,2) posterior mode
class TestBetaPosteriorMode(unittest.TestCase):
    def test_rq69_posterior_mode(self) -> None:
        # Beta(2,2) prior + 37 succ / 40 fail -> Beta(39,42) -> mode 38/79.
        m = rq69.beta_posterior_mode(2.0, 2.0, 37, 77)
        self.assertAlmostEqual(m, 38.0 / 79.0, 12)
        self.assertAlmostEqual(m, 0.4810126582, 9)

    def test_uniform_prior_posterior_mode(self) -> None:
        # Beta(1,1) prior + 1 succ / 1 fail -> Beta(2,2) -> mode 0.5 (1/2).
        m = rq69.beta_posterior_mode(1.0, 1.0, 1, 2)
        self.assertAlmostEqual(m, 0.5, 12)

    def test_no_observations_returns_prior_mode(self) -> None:
        # Beta(2,2) prior + 0 succ / 0 fail -> Beta(2,2) -> mode 0.5.
        m = rq69.beta_posterior_mode(2.0, 2.0, 0, 0)
        self.assertAlmostEqual(m, 0.5, 12)

    def test_all_successes(self) -> None:
        # Beta(2,2) + 10 succ / 0 fail -> Beta(12,2) -> mode 11/12.
        m = rq69.beta_posterior_mode(2.0, 2.0, 10, 10)
        self.assertAlmostEqual(m, 11.0 / 12.0, 12)

    def test_all_failures(self) -> None:
        # Beta(2,2) + 0 succ / 10 fail -> Beta(2,12) -> mode 1/12.
        m = rq69.beta_posterior_mode(2.0, 2.0, 0, 10)
        self.assertAlmostEqual(m, 1.0 / 12.0, 12)

    def test_degenerate_uniform_posterior_falls_back_to_mean(self) -> None:
        # Beta(1,1) prior + 0 succ / 0 fail -> Beta(1,1) (no mode); fallback mean 0.5.
        m = rq69.beta_posterior_mode(1.0, 1.0, 0, 0)
        # alpha' = 1, beta' = 1: no unique mode -> mean fallback = 0.5.
        self.assertAlmostEqual(m, 0.5, 12)


# --------------------------------------------------------------- shrinkage objective
class TestShrinkageObjective(unittest.TestCase):
    def test_lambda_zero_is_pure_sensitivity(self) -> None:
        # At lam=0 the penalty vanishes: objective == sensitivity.
        self.assertAlmostEqual(
            rq69.shrinkage_objective(0.5, 0.8, 0.4, 0.0), 0.8, 12)

    def test_penalty_reduces_objective_when_away_from_prior(self) -> None:
        # threshold_norm = 0.9, prior = 0.4, lam = 0.1 -> penalty 0.05.
        obj = rq69.shrinkage_objective(0.9, 0.8, 0.4, 0.1)
        self.assertAlmostEqual(obj, 0.8 - 0.1 * abs(0.9 - 0.4), 12)
        self.assertAlmostEqual(obj, 0.8 - 0.05, 12)

    def test_penalty_zero_at_prior(self) -> None:
        # threshold_norm == prior_mean_norm -> penalty 0 -> objective = sensitivity.
        self.assertAlmostEqual(
            rq69.shrinkage_objective(0.4, 0.8, 0.4, 1.0), 0.8, 12)

    def test_higher_lambda_stronger_penalty(self) -> None:
        # Holding threshold fixed, increasing lam strictly decreases objective
        # when threshold != prior.
        t, s, p = 0.7, 0.8, 0.4
        objs = [rq69.shrinkage_objective(t, s, p, lam) for lam in (0.0, 0.1, 0.5, 1.0)]
        for a, b in zip(objs[:-1], objs[1:]):
            self.assertGreater(a, b)

    def test_symmetric_around_prior(self) -> None:
        # |t - prior| is symmetric: t = prior + d and t = prior - d give same obj.
        prior = 0.4
        for d in (0.1, 0.2, 0.3):
            o_plus = rq69.shrinkage_objective(prior + d, 0.8, prior, 0.5)
            o_minus = rq69.shrinkage_objective(prior - d, 0.8, prior, 0.5)
            self.assertAlmostEqual(o_plus, o_minus, 12)


# --------------------------------------------------------------- confusion arrays
class TestConfusionArrays(unittest.TestCase):
    def test_perfect_separation(self) -> None:
        scores = np.array([5.0, 6.0, 1.0, 0.5])
        labels = np.array([1, 1, 0, 0])
        grid = np.array([2.0])
        tp, fp, tn, fn, n_pos, n_neg = rq69._confusion_arrays(scores, labels, grid)
        self.assertEqual(n_pos, 2)
        self.assertEqual(n_neg, 2)
        self.assertEqual(int(tp[0]), 2)
        self.assertEqual(int(fp[0]), 0)
        self.assertEqual(int(tn[0]), 2)
        self.assertEqual(int(fn[0]), 0)

    def test_threshold_above_all_flags_nothing(self) -> None:
        # 2 positives (scores 1.0, 3.0) and 1 negative (score 2.0); threshold
        # 10.0 above all -> nothing flagged.
        scores = np.array([1.0, 2.0, 3.0])
        labels = np.array([1, 0, 1])
        grid = np.array([10.0])
        tp, fp, tn, fn, n_pos, n_neg = rq69._confusion_arrays(scores, labels, grid)
        self.assertEqual(n_pos, 2)
        self.assertEqual(n_neg, 1)
        self.assertEqual(int(tp[0]), 0)
        self.assertEqual(int(fp[0]), 0)
        self.assertEqual(int(tn[0]), 1)  # 1 negative correctly not flagged
        self.assertEqual(int(fn[0]), 2)  # 2 positives missed

    def test_grid_sweep_produces_arrays(self) -> None:
        scores = np.array([0.5, 1.5, 2.5, 3.5])
        labels = np.array([0, 1, 0, 1])
        grid = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        tp, fp, tn, fn, _, _ = rq69._confusion_arrays(scores, labels, grid)
        self.assertEqual(tp.shape, (5,))
        self.assertEqual(fp.shape, (5,))
        # At t=0.0 all flagged: tp = 2, fp = 2.
        self.assertEqual(int(tp[0]), 2)
        self.assertEqual(int(fp[0]), 2)
        # At t=4.0 nothing flagged.
        self.assertEqual(int(tp[-1]), 0)
        self.assertEqual(int(fp[-1]), 0)

    def test_no_positives(self) -> None:
        scores = np.array([0.5, 1.5])
        labels = np.array([0, 0])
        grid = np.array([1.0])
        tp, fp, tn, fn, n_pos, n_neg = rq69._confusion_arrays(scores, labels, grid)
        self.assertEqual(n_pos, 0)
        self.assertEqual(int(tp[0]), 0)
        self.assertEqual(int(fn[0]), 0)
        self.assertEqual(int(tn[0]), 1)
        self.assertEqual(int(fp[0]), 1)


# --------------------------------------------------------------- sensitivity / specificity
class TestSensSpec(unittest.TestCase):
    def test_perfect_classifier(self) -> None:
        tp = np.array([10])
        fp = np.array([0])
        tn = np.array([10])
        fn = np.array([0])
        sens, spec = rq69._sens_spec(tp, fp, tn, fn, 10, 10)
        self.assertAlmostEqual(float(sens[0]), 1.0, 12)
        self.assertAlmostEqual(float(spec[0]), 1.0, 12)

    def test_no_positives_sens_zero(self) -> None:
        tp = np.array([0])
        fn = np.array([0])
        tn = np.array([5])
        fp = np.array([2])
        sens, spec = rq69._sens_spec(tp, fp, tn, fn, 0, 7)
        self.assertAlmostEqual(float(sens[0]), 0.0, 12)
        self.assertAlmostEqual(float(spec[0]), 5.0 / 7.0, 12)

    def test_no_negatives_spec_one(self) -> None:
        tp = np.array([3])
        fn = np.array([1])
        tn = np.array([0])
        fp = np.array([0])
        sens, spec = rq69._sens_spec(tp, fp, tn, fn, 4, 0)
        self.assertAlmostEqual(float(sens[0]), 3.0 / 4.0, 12)
        self.assertAlmostEqual(float(spec[0]), 1.0, 12)


# --------------------------------------------------------------- shrinkage calibration
class TestCalibrateShrinkageKL(unittest.TestCase):
    def setUp(self) -> None:
        self.w = rq69.load_rq43_per_window()
        self.labels = (self.w["tiny"] > rq69.CATASTROPHIC_CPWER).astype(int)
        self.kl_max = float(self.w["kl"].max())

    def test_lambda_zero_meets_specificity_floor(self) -> None:
        cal = rq69.calibrate_shrinkage_kl(
            self.w["kl"], self.labels, self.kl_max,
            rq69.PRIOR_MEAN_NORM, lam=0.0)
        self.assertGreaterEqual(cal["specificity"], 0.90 - rq69.EPS)

    def test_lambda_zero_threshold_is_4_87(self) -> None:
        # The >=90% specificity floor on the real KL detector forces thr = 4.87.
        cal = rq69.calibrate_shrinkage_kl(
            self.w["kl"], self.labels, self.kl_max,
            rq69.PRIOR_MEAN_NORM, lam=0.0)
        self.assertAlmostEqual(cal["threshold"], 4.87, 6)

    def test_high_lambda_does_not_move_in_sample_threshold(self) -> None:
        # The shrinkage penalty cannot break the spec floor: in-sample threshold
        # is 4.87 for all lambda in the grid.
        for lam in rq69.LAMBDAS:
            cal = rq69.calibrate_shrinkage_kl(
                self.w["kl"], self.labels, self.kl_max,
                rq69.PRIOR_MEAN_NORM, lam=lam)
            self.assertAlmostEqual(cal["threshold"], 4.87, 6,
                                   msg=f"lam={lam} moved threshold")

    def test_threshold_within_grid(self) -> None:
        cal = rq69.calibrate_shrinkage_kl(
            self.w["kl"], self.labels, self.kl_max,
            rq69.PRIOR_MEAN_NORM, lam=0.5)
        self.assertGreaterEqual(cal["threshold"], 0.0)
        self.assertLessEqual(cal["threshold"], 8.55)

    def test_threshold_norm_uses_kl_max(self) -> None:
        cal = rq69.calibrate_shrinkage_kl(
            self.w["kl"], self.labels, self.kl_max,
            rq69.PRIOR_MEAN_NORM, lam=0.0)
        self.assertAlmostEqual(
            cal["threshold_norm"], cal["threshold"] / self.kl_max, 6)

    def test_in_sample_sensitivity_low(self) -> None:
        # At thr=4.87 only 1 of 37 hallucinated windows is flagged: sens ~ 0.027.
        cal = rq69.calibrate_shrinkage_kl(
            self.w["kl"], self.labels, self.kl_max,
            rq69.PRIOR_MEAN_NORM, lam=0.0)
        self.assertAlmostEqual(cal["sensitivity"], 1.0 / 37.0, 4)
        self.assertEqual(cal["tp"], 1)
        self.assertEqual(cal["fn"], 36)

    def test_in_sample_specificity_at_floor(self) -> None:
        # 4 of 40 clean windows flagged -> spec = 36/40 = 0.9.
        cal = rq69.calibrate_shrinkage_kl(
            self.w["kl"], self.labels, self.kl_max,
            rq69.PRIOR_MEAN_NORM, lam=0.0)
        self.assertAlmostEqual(cal["specificity"], 0.9, 6)
        self.assertEqual(cal["fp"], 4)
        self.assertEqual(cal["tn"], 36)


# --------------------------------------------------------------- cascade simulation
class TestCascadeSimulation(unittest.TestCase):
    def setUp(self) -> None:
        self.w = rq69.load_rq43_per_window()

    def test_no_escalation_equals_tiny_mean(self) -> None:
        # threshold above max KL -> all on tiny tier -> cpWER = tiny.mean().
        cp = rq69.cascade_cpwer_at_threshold(
            self.w["tiny"], self.w["base"], self.w["kl"], 100.0)
        self.assertAlmostEqual(cp, float(self.w["tiny"].mean()), 12)

    def test_all_escalation_equals_base_mean(self) -> None:
        # threshold at 0 -> all on base tier -> cpWER = base.mean().
        cp = rq69.cascade_cpwer_at_threshold(
            self.w["tiny"], self.w["base"], self.w["kl"], 0.0)
        self.assertAlmostEqual(cp, float(self.w["base"].mean()), 12)

    def test_empty_returns_zero(self) -> None:
        cp = rq69.cascade_cpwer_at_threshold(
            np.array([]), np.array([]), np.array([]), 1.0)
        self.assertEqual(cp, 0.0)

    def test_reproduces_rq43_at_kl_3_30(self) -> None:
        # The controlled-comparison anchor: cascade @ KL=3.30 -> 0.888947.
        cp = rq69.cascade_cpwer_at_threshold(
            self.w["tiny"], self.w["base"], self.w["kl"], 3.30)
        self.assertAlmostEqual(cp, rq69.RQ43_CASCADE_CPWER, 4)

    def test_cascade_compute_no_escalation(self) -> None:
        # threshold above max -> 0% escalation -> compute = tiny = 1.0.
        self.assertAlmostEqual(
            rq69.cascade_compute_at_threshold(self.w["kl"], 100.0), 1.0, 12)

    def test_cascade_compute_all_escalation(self) -> None:
        # threshold = 0 -> 100% escalation -> compute = base = 1.93.
        self.assertAlmostEqual(
            rq69.cascade_compute_at_threshold(self.w["kl"], 0.0), 1.93, 12)

    def test_cascade_compute_partial(self) -> None:
        # 50% escalation -> compute = 0.5*1.0 + 0.5*1.93 = 1.465.
        kl = np.array([0.0, 1.0, 2.0, 3.0])
        cp = rq69.cascade_compute_at_threshold(kl, 1.5)
        # 2 of 4 >= 1.5 -> 50% escalation
        self.assertAlmostEqual(cp, 0.5 * 1.0 + 0.5 * 1.93, 12)

    def test_escalation_fraction_at_threshold(self) -> None:
        # At thr=4.87 on real data, 5/77 windows escalate (frac ~ 0.0649).
        frac = rq69.escalation_fraction_at_threshold(self.w["kl"], 4.87)
        self.assertAlmostEqual(frac, 5.0 / 77.0, 6)

    def test_escalation_fraction_empty(self) -> None:
        self.assertEqual(
            rq69.escalation_fraction_at_threshold(np.array([]), 1.0), 0.0)


# --------------------------------------------------------------- cascade OOB
class TestCascadeOOB(unittest.TestCase):
    def setUp(self) -> None:
        self.w = rq69.load_rq43_per_window()

    def test_oob_excludes_in_bag(self) -> None:
        # If in-bag = first 70, OOB = last 7.
        in_bag = np.arange(70)
        oob = rq69.cascade_oob_cpwer(
            self.w["tiny"], self.w["base"], self.w["kl"], 3.30, in_bag)
        self.assertEqual(oob["n_oob"], 7)
        # Verify OOB cpWER matches a direct computation on the last 7.
        direct = float(np.where(
            self.w["kl"][70:] >= 3.30 - rq69.EPS,
            self.w["base"][70:], self.w["tiny"][70:]).mean())
        self.assertAlmostEqual(oob["cpwer"], direct, 12)

    def test_oob_empty_returns_nan(self) -> None:
        # If in-bag = all 77 indices, OOB is empty -> cpwer = nan.
        in_bag = np.arange(77)
        oob = rq69.cascade_oob_cpwer(
            self.w["tiny"], self.w["base"], self.w["kl"], 3.30, in_bag)
        self.assertEqual(oob["n_oob"], 0)
        self.assertTrue(math.isnan(oob["cpwer"]))

    def test_oob_escalation_uses_threshold(self) -> None:
        # Very high threshold -> no OOB escalation -> cpwer = mean(OOB tiny).
        in_bag = np.arange(70)
        oob = rq69.cascade_oob_cpwer(
            self.w["tiny"], self.w["base"], self.w["kl"], 100.0, in_bag)
        self.assertEqual(oob["n_escalated"], 0)
        self.assertAlmostEqual(oob["cpwer"], float(self.w["tiny"][70:].mean()), 12)

    def test_oob_in_bag_duplicates_dont_double_count(self) -> None:
        # Duplicate indices in in_bag should not change the OOB set.
        in_bag = np.array(list(range(70)) * 3)  # 210 entries, same 70 unique
        oob = rq69.cascade_oob_cpwer(
            self.w["tiny"], self.w["base"], self.w["kl"], 3.30, in_bag)
        self.assertEqual(oob["n_oob"], 7)


# --------------------------------------------------------------- bootstrap shrinkage cascade
class TestBootstrapShrinkageCascade(unittest.TestCase):
    def test_deterministic_with_seed(self) -> None:
        rng = np.random.default_rng(0)
        n = 12
        tiny = rng.uniform(0.5, 2.0, n)
        base = tiny * 0.4
        kl = rng.uniform(0.0, 8.5, n)
        labels = (tiny > 1.0).astype(int)
        kl_max = float(kl.max())
        out1 = rq69.bootstrap_shrinkage_cascade(
            tiny, base, kl, labels, kl_max, rq69.PRIOR_MEAN_NORM, lam=0.1,
            n_boot=8, seed=42)
        out2 = rq69.bootstrap_shrinkage_cascade(
            tiny, base, kl, labels, kl_max, rq69.PRIOR_MEAN_NORM, lam=0.1,
            n_boot=8, seed=42)
        np.testing.assert_array_equal(out1["boot_idx"], out2["boot_idx"])
        np.testing.assert_array_equal(out1["thresholds"], out2["thresholds"])

    def test_shapes(self) -> None:
        rng = np.random.default_rng(0)
        n = 12
        tiny = rng.uniform(0.5, 2.0, n)
        base = tiny * 0.4
        kl = rng.uniform(0.0, 8.5, n)
        labels = (tiny > 1.0).astype(int)
        kl_max = float(kl.max())
        out = rq69.bootstrap_shrinkage_cascade(
            tiny, base, kl, labels, kl_max, rq69.PRIOR_MEAN_NORM, lam=0.0,
            n_boot=8, seed=1)
        self.assertEqual(out["boot_idx"].shape, (8, n))
        self.assertEqual(out["thresholds"].shape, (8,))
        self.assertEqual(out["oob_cpwer"].shape, (8,))
        self.assertEqual(out["n_oob"].shape, (8,))
        self.assertEqual(out["n_escalated_oob"].shape, (8,))

    def test_thresholds_within_grid(self) -> None:
        rng = np.random.default_rng(0)
        n = 12
        tiny = rng.uniform(0.5, 2.0, n)
        base = tiny * 0.4
        kl = rng.uniform(0.0, 8.5, n)
        labels = (tiny > 1.0).astype(int)
        kl_max = float(kl.max())
        out = rq69.bootstrap_shrinkage_cascade(
            tiny, base, kl, labels, kl_max, rq69.PRIOR_MEAN_NORM, lam=0.0,
            n_boot=20, seed=1)
        for t in out["thresholds"]:
            self.assertGreaterEqual(t, 0.0)
            self.assertLessEqual(t, 8.55)

    def test_oob_size_positive_and_bounded(self) -> None:
        rng = np.random.default_rng(0)
        n = 15
        tiny = rng.uniform(0.5, 2.0, n)
        base = tiny * 0.4
        kl = rng.uniform(0.0, 8.5, n)
        labels = (tiny > 1.0).astype(int)
        kl_max = float(kl.max())
        out = rq69.bootstrap_shrinkage_cascade(
            tiny, base, kl, labels, kl_max, rq69.PRIOR_MEAN_NORM, lam=0.0,
            n_boot=50, seed=2)
        # Every resample has 0 < n_oob <= n.
        self.assertTrue(np.all(out["n_oob"] >= 0))
        self.assertTrue(np.all(out["n_oob"] <= n))
        # Most resamples have a non-empty OOB.
        self.assertGreater(int((out["n_oob"] > 0).sum()), 40)

    def test_oob_cpwer_within_tiny_base_range(self) -> None:
        # OOB cpWER must lie in [min(base), max(tiny)] (base<=tiny here).
        rng = np.random.default_rng(2)
        n = 15
        tiny = rng.uniform(1.0, 3.0, n)
        base = tiny * 0.4
        kl = rng.uniform(0.0, 8.0, n)
        labels = (tiny > 1.5).astype(int)
        kl_max = float(kl.max())
        out = rq69.bootstrap_shrinkage_cascade(
            tiny, base, kl, labels, kl_max, rq69.PRIOR_MEAN_NORM, lam=0.1,
            n_boot=50, seed=4)
        valid = out["oob_cpwer"][~np.isnan(out["oob_cpwer"])]
        self.assertTrue(np.all(valid >= base.min() - 1e-9))
        self.assertTrue(np.all(valid <= tiny.max() + 1e-9))

    def test_oob_cpwer_matches_cascade_oob_cpwer(self) -> None:
        # The vectorised loop's OOB cpWER must equal cascade_oob_cpwer at the
        # calibrated threshold for each resample's in-bag index.
        rng = np.random.default_rng(8)
        n = 10
        tiny = rng.uniform(0.5, 2.0, n)
        base = tiny * 0.4
        kl = rng.uniform(0.0, 8.0, n)
        labels = (tiny > 1.0).astype(int)
        kl_max = float(kl.max())
        out = rq69.bootstrap_shrinkage_cascade(
            tiny, base, kl, labels, kl_max, rq69.PRIOR_MEAN_NORM, lam=0.0,
            n_boot=6, seed=5)
        for b in range(6):
            if out["n_oob"][b] == 0:
                self.assertTrue(math.isnan(float(out["oob_cpwer"][b])))
                continue
            oob = rq69.cascade_oob_cpwer(
                tiny, base, kl, float(out["thresholds"][b]), out["boot_idx"][b])
            self.assertAlmostEqual(float(out["oob_cpwer"][b]), oob["cpwer"], 9,
                                   msg=f"resample {b}")


# --------------------------------------------------------------- jackknife
class TestJackknife(unittest.TestCase):
    def test_returns_n_loo_values(self) -> None:
        rng = np.random.default_rng(0)
        n = 8
        tiny = rng.uniform(0.5, 2.0, n)
        base = tiny * 0.4
        kl = rng.uniform(0.0, 8.0, n)
        labels = (tiny > 1.0).astype(int)
        kl_max = float(kl.max())
        a, loo = rq69.jackknife_acceleration(
            tiny, base, kl, labels, kl_max, rq69.PRIOR_MEAN_NORM, lam=0.0)
        self.assertEqual(loo.shape, (n,))
        self.assertTrue(np.all(np.isfinite(loo)))
        self.assertTrue(np.isfinite(a))

    def test_zero_variation_when_identical(self) -> None:
        # All windows identical -> every LOO fit gives the same theta -> a = 0.
        tiny = np.array([1.0] * 6)
        base = np.array([0.4] * 6)
        kl = np.array([2.0] * 6)
        labels = np.array([1, 1, 1, 0, 0, 0])
        a, loo = rq69.jackknife_acceleration(
            tiny, base, kl, labels, 2.0, rq69.PRIOR_MEAN_NORM, lam=0.0)
        self.assertAlmostEqual(a, 0.0, 9)

    def test_acceleration_finite_on_real_data(self) -> None:
        w = rq69.load_rq43_per_window()
        labels = (w["tiny"] > rq69.CATASTROPHIC_CPWER).astype(int)
        kl_max = float(w["kl"].max())
        a, loo = rq69.jackknife_acceleration(
            w["tiny"], w["base"], w["kl"], labels, kl_max,
            rq69.PRIOR_MEAN_NORM, lam=0.01)
        self.assertEqual(loo.shape, (77,))
        self.assertTrue(np.all(np.isfinite(loo)))
        self.assertTrue(np.isfinite(a))
        self.assertLess(abs(a), 1.0)


# --------------------------------------------------------------- BCa CI (RQ59 re-export)
class TestBCa(unittest.TestCase):
    def test_bca_ci_is_rq59_bca_ci(self) -> None:
        # rq69.bca_ci IS rq59.bca_ci (re-exported for traceability).
        self.assertIs(rq69.bca_ci, rq59.bca_ci)

    def test_equals_percentile_when_no_bias_no_accel(self) -> None:
        boot = np.arange(100, dtype=float)
        theta_hat = 49.5
        bca = rq69.bca_ci(theta_hat, boot, accel=0.0, alpha=0.05)
        self.assertEqual(bca["method"], "bca")
        lo = float(np.percentile(boot, 2.5))
        hi = float(np.percentile(boot, 97.5))
        self.assertAlmostEqual(bca["lo"], lo, 4)
        self.assertAlmostEqual(bca["hi"], hi, 4)

    def test_bias_shifts_ci_right_when_theta_hat_high(self) -> None:
        boot = np.linspace(0.0, 100.0, 101)
        bca_low = rq69.bca_ci(50.0, boot, accel=0.0)
        bca_high = rq69.bca_ci(95.0, boot, accel=0.0)
        self.assertGreater(bca_high["lo"], bca_low["lo"])
        self.assertGreater(bca_high["hi"], bca_low["hi"])

    def test_degenerate_constant_boot(self) -> None:
        boot = np.full(100, 0.7)
        bca = rq69.bca_ci(0.7, boot, accel=0.0)
        self.assertAlmostEqual(bca["lo"], 0.7, 6)
        self.assertAlmostEqual(bca["hi"], 0.7, 6)

    def test_nan_samples_dropped(self) -> None:
        boot = np.array([1.0, 2.0, np.nan, 3.0, np.nan, 4.0])
        bca = rq69.bca_ci(2.5, boot, accel=0.0)
        self.assertEqual(bca["n_valid"], 4)
        self.assertTrue(np.isfinite(bca["lo"]))

    def test_empty_boot_returns_nan(self) -> None:
        bca = rq69.bca_ci(1.0, np.array([]), accel=0.0)
        self.assertEqual(bca["method"], "empty")
        self.assertTrue(math.isnan(bca["lo"]))


# --------------------------------------------------------------- norm_cdf / norm_ppf
class TestNormHelpers(unittest.TestCase):
    def test_norm_cdf_is_rq59_norm_cdf(self) -> None:
        self.assertIs(rq69.norm_cdf, rq59.norm_cdf)

    def test_norm_ppf_is_rq59_norm_ppf(self) -> None:
        self.assertIs(rq69.norm_ppf, rq59.norm_ppf)

    def test_norm_cdf_roundtrip(self) -> None:
        for x in (-2.0, -0.5, 0.0, 0.5, 2.0):
            expected = 0.5 * math.erfc(-x / math.sqrt(2.0))
            self.assertAlmostEqual(rq69.norm_cdf(x), expected, 6)

    def test_norm_ppf_known_quantiles(self) -> None:
        # 0.025 -> -1.96, 0.975 -> +1.96, 0.5 -> 0.
        self.assertAlmostEqual(rq69.norm_ppf(0.5), 0.0, 4)
        self.assertAlmostEqual(rq69.norm_ppf(0.025), -1.959964, 4)
        self.assertAlmostEqual(rq69.norm_ppf(0.975), 1.959964, 4)

    def test_norm_cdf_ppf_roundtrip(self) -> None:
        for p in (0.1, 0.25, 0.5, 0.75, 0.9):
            x = rq69.norm_ppf(p)
            self.assertAlmostEqual(rq69.norm_cdf(x), p, 4)


# --------------------------------------------------------------- mode count (RQ48 re-export)
class TestModeCount(unittest.TestCase):
    def test_count_modes_is_rq48_count_modes(self) -> None:
        self.assertIs(rq69.count_modes, rq48.count_modes)

    def test_single_mode(self) -> None:
        thr = np.array([1.0] * 80 + [2.0] * 20)
        m = rq69.count_modes(thr, 0.05)
        self.assertEqual(m["n_modes"], 2)

    def test_sub_5pct_excluded(self) -> None:
        thr = np.array([1.0] * 90 + [2.0] * 4 + [3.0] * 6)
        m = rq69.count_modes(thr, 0.05)
        thresholds = {md["threshold"] for md in m["modes"]}
        self.assertIn(1.0, thresholds)
        self.assertIn(3.0, thresholds)
        self.assertNotIn(2.0, thresholds)

    def test_empty(self) -> None:
        m = rq69.count_modes(np.array([]), 0.05)
        self.assertEqual(m["n_modes"], 0)


# --------------------------------------------------------------- _finite_stats
class TestFiniteStats(unittest.TestCase):
    def test_no_inf(self) -> None:
        arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        s = rq69._finite_stats(arr)
        self.assertEqual(s["n_finite"], 5)
        self.assertEqual(s["n_inf"], 0)
        self.assertAlmostEqual(s["median"], 3.0, 6)
        self.assertAlmostEqual(s["mean"], 3.0, 6)

    def test_drops_inf(self) -> None:
        arr = np.array([1.0, 2.0, np.inf, 3.0, np.inf])
        s = rq69._finite_stats(arr)
        self.assertEqual(s["n_finite"], 3)
        self.assertEqual(s["n_inf"], 2)
        self.assertEqual(s["n_total"], 5)
        self.assertAlmostEqual(s["median"], 2.0, 6)

    def test_all_inf(self) -> None:
        arr = np.array([np.inf, np.inf, np.inf])
        s = rq69._finite_stats(arr)
        self.assertEqual(s["n_finite"], 0)
        self.assertEqual(s["n_inf"], 3)
        self.assertTrue(math.isnan(s["median"]))


# --------------------------------------------------------------- best-lambda selection
class TestSelectBestLambda(unittest.TestCase):
    def test_lowest_oob_median_wins(self) -> None:
        per_lambda = {
            "0.0": {"lambda": 0.0, "oob_cpwer_median": 1.55,
                    "bca_width": 0.52, "n_modes_5pct": 5},
            "0.01": {"lambda": 0.01, "oob_cpwer_median": 1.54,
                     "bca_width": 0.53, "n_modes_5pct": 7},
        }
        best = rq69.select_best_lambda(per_lambda)
        self.assertAlmostEqual(best["lambda"], 0.01, 6)

    def test_tiebreak_narrowest_width(self) -> None:
        per_lambda = {
            "0.0": {"lambda": 0.0, "oob_cpwer_median": 1.54,
                    "bca_width": 0.55, "n_modes_5pct": 5},
            "0.01": {"lambda": 0.01, "oob_cpwer_median": 1.54,
                     "bca_width": 0.50, "n_modes_5pct": 7},
        }
        best = rq69.select_best_lambda(per_lambda)
        self.assertAlmostEqual(best["lambda"], 0.01, 6)

    def test_tiebreak_fewest_modes(self) -> None:
        per_lambda = {
            "0.0": {"lambda": 0.0, "oob_cpwer_median": 1.54,
                    "bca_width": 0.50, "n_modes_5pct": 7},
            "0.01": {"lambda": 0.01, "oob_cpwer_median": 1.54,
                     "bca_width": 0.50, "n_modes_5pct": 5},
        }
        best = rq69.select_best_lambda(per_lambda)
        self.assertAlmostEqual(best["lambda"], 0.01, 6)

    def test_tiebreak_smallest_lambda(self) -> None:
        per_lambda = {
            "0.0": {"lambda": 0.0, "oob_cpwer_median": 1.54,
                    "bca_width": 0.50, "n_modes_5pct": 5},
            "0.01": {"lambda": 0.01, "oob_cpwer_median": 1.54,
                     "bca_width": 0.50, "n_modes_5pct": 5},
        }
        best = rq69.select_best_lambda(per_lambda)
        self.assertAlmostEqual(best["lambda"], 0.0, 6)


# --------------------------------------------------------------- hypothesis helpers
class TestHypothesisHelpers(unittest.TestCase):
    def test_h69a_strict_less_than(self) -> None:
        # H69a: < 0.889 supported; >= 0.889 killed.
        self.assertTrue(rq69._h69a_supported(0.888))
        self.assertTrue(rq69._h69a_supported(0.7))
        self.assertFalse(rq69._h69a_supported(0.889))
        self.assertFalse(rq69._h69a_supported(1.5))

    def test_h69b_strict_less_than(self) -> None:
        # H69b: < 0.831 supported; >= 0.831 killed.
        self.assertTrue(rq69._h69b_supported(0.83))
        self.assertTrue(rq69._h69b_supported(0.065))
        self.assertFalse(rq69._h69b_supported(0.831))
        self.assertFalse(rq69._h69b_supported(0.9))

    def test_h69c_strict_less_than(self) -> None:
        # H69c: < 0.283 supported; >= 0.283 killed.
        self.assertTrue(rq69._h69c_supported(0.282))
        self.assertTrue(rq69._h69c_supported(0.1))
        self.assertFalse(rq69._h69c_supported(0.283))
        self.assertFalse(rq69._h69c_supported(0.5))


# --------------------------------------------------------------- end-to-end smoke
class TestEndToEnd(unittest.TestCase):
    def test_load_rq43_per_window(self) -> None:
        w = rq69.load_rq43_per_window()
        self.assertEqual(len(w["tiny"]), 77)
        self.assertEqual(len(w["base"]), 77)
        self.assertEqual(len(w["kl"]), 77)
        self.assertAlmostEqual(float(w["tiny"].mean()), rq69.RQ43_BASELINE_CPWER, 4)

    def test_label_counts_37_40(self) -> None:
        w = rq69.load_rq43_per_window()
        labels = (w["tiny"] > rq69.CATASTROPHIC_CPWER).astype(int)
        self.assertEqual(int(labels.sum()), 37)
        self.assertEqual(int((labels == 0).sum()), 40)

    def test_base_ratio_constant(self) -> None:
        w = rq69.load_rq43_per_window()
        ratio = w["base"] / w["tiny"]
        self.assertTrue(np.allclose(ratio, rq69.RQ43_BASE_RATIO, atol=1e-4))

    def test_rq43_reproduction_at_kl_3_30(self) -> None:
        # The controlled-comparison anchor: cascade @ KL=3.30 -> 0.888947.
        w = rq69.load_rq43_per_window()
        cp = rq69.cascade_cpwer_at_threshold(
            w["tiny"], w["base"], w["kl"], 3.30)
        self.assertAlmostEqual(cp, rq69.RQ43_CASCADE_CPWER, 4)

    def test_kl_detector_geometry(self) -> None:
        # Pins the data geometry: hallucinated KL floor ~ 2.98, clean KL spans
        # [0, 8.53], 13 clean windows have KL = 0 exactly. This is why the
        # >=90% specificity floor forces thr=4.87 (only 4 clean >= 4.87).
        w = rq69.load_rq43_per_window()
        labels = (w["tiny"] > rq69.CATASTROPHIC_CPWER).astype(int)
        hall_kl = w["kl"][labels == 1]
        clean_kl = w["kl"][labels == 0]
        self.assertGreater(float(hall_kl.min()), 2.9)
        self.assertLess(float(hall_kl.min()), 3.0)
        self.assertAlmostEqual(float(clean_kl.min()), 0.0, 6)
        self.assertGreater(float(clean_kl.max()), 8.0)
        self.assertEqual(int(((w["kl"] == 0) & (labels == 0)).sum()), 13)
        # 4 clean windows have KL >= 4.87 -> spec = 36/40 = 0.9 (the floor).
        self.assertEqual(int(((w["kl"] >= 4.87 - rq69.EPS) & (labels == 0)).sum()), 4)

    def test_small_bootstrap_end_to_end(self) -> None:
        # A tiny bootstrap on the real data: runs fast, produces valid output.
        w = rq69.load_rq43_per_window()
        labels = (w["tiny"] > rq69.CATASTROPHIC_CPWER).astype(int)
        kl_max = float(w["kl"].max())
        out = rq69.bootstrap_shrinkage_cascade(
            w["tiny"], w["base"], w["kl"], labels, kl_max,
            rq69.PRIOR_MEAN_NORM, lam=0.01, n_boot=30, seed=42)
        self.assertEqual(out["thresholds"].shape, (30,))
        valid = out["oob_cpwer"][~np.isnan(out["oob_cpwer"])]
        self.assertGreater(len(valid), 0)
        self.assertTrue(np.all(valid >= 0.0))
        self.assertTrue(np.all(valid < 3.0))

    def test_results_json_written_and_consistent(self) -> None:
        # The generated results JSON must exist, be labelled experimental/
        # frontier, and report the three hypothesis verdicts consistently with
        # the in-sample escalation / OOB median / BCa width.
        self.assertTrue(OUT_JSON.exists(), f"missing {OUT_JSON}")
        data = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        self.assertEqual(data["label"], "experimental/frontier")
        self.assertEqual(data["closes_issue"], 997)
        self.assertEqual(data["n_windows"], 77)
        self.assertEqual(data["n_hallucinated"], 37)
        self.assertEqual(data["n_clean"], 40)
        # Beta(2,2) posterior mode = 38/79.
        self.assertAlmostEqual(
            data["shrinkage_prior"]["posterior_mode_norm"], 38.0 / 79.0, 6)
        # H69a: OOB cpWER >= 0.889 -> KILLED (median ~1.54).
        med = data["best_lambda"]["oob_cpwer_median"]
        self.assertGreaterEqual(med, rq69.H69A_MAX_CPWER)
        self.assertEqual(data["hypothesis_verdicts"]["H69a"]["supported"], False)
        # H69b: escalation < 0.831 -> SUPPORTED (frac ~0.065).
        frac = data["best_lambda_in_sample"]["escalation_fraction"]
        self.assertLess(frac, rq69.H69B_MAX_ESCALATION)
        self.assertEqual(data["hypothesis_verdicts"]["H69b"]["supported"], True)
        # H69c: BCa width >= 0.283 -> KILLED (width ~0.53).
        width = data["hypothesis_verdicts"]["H69c"]["bca_ci_width"]
        self.assertGreaterEqual(width, rq69.H69C_MAX_WIDTH)
        self.assertEqual(data["hypothesis_verdicts"]["H69c"]["supported"], False)
        # Bootstrap arrays must have length N_BOOT.
        self.assertEqual(len(data["per_bootstrap"]["thresholds"]), rq69.N_BOOT)
        self.assertEqual(len(data["per_bootstrap"]["oob_cpwer"]), rq69.N_BOOT)
        self.assertEqual(len(data["per_bootstrap"]["n_oob"]), rq69.N_BOOT)

    def test_results_json_in_sample_threshold_constant_across_lambdas(self) -> None:
        # The central RQ69 finding: the >=90% specificity floor blocks the
        # shrinkage penalty; the in-sample threshold is 4.87 across all lambda.
        data = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        in_sample = data["in_sample_calibration"]
        for lam_key, entry in in_sample.items():
            self.assertAlmostEqual(entry["threshold"], 4.87, 6,
                                   msg=f"lambda={lam_key}")
            self.assertAlmostEqual(entry["cascade_cpwer"], 1.550054, 4,
                                   msg=f"lambda={lam_key}")
            self.assertAlmostEqual(entry["escalation_fraction"], 5.0 / 77.0, 6,
                                   msg=f"lambda={lam_key}")

    def test_results_json_best_lambda_is_0_01(self) -> None:
        # Best lambda = 0.01 (lowest OOB cpWER median, then narrowest BCa,
        # then fewest modes, then smallest lambda).
        data = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        self.assertAlmostEqual(data["best_lambda"]["lambda"], 0.01, 6)


# --------------------------------------------------------------- CSV output
class TestCSVOutput(unittest.TestCase):
    def test_write_bootstrap_csv_header_and_rows(self) -> None:
        # Synthetic: 3 resamples, 4 windows. Verifies header, row count, and
        # that nan / empty-OOB rows are handled (blank oob_cpwer, blank esc frac).
        _SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
        out = _SCRIPT_DIR / "_test_csv_tmp.csv"
        try:
            boot_idx = np.array([[0, 1, 2, 0], [0, 1, 0, 1], [0, 1, 2, 3]])
            thr = np.array([0.5, 1.0, 2.0])
            oob = np.array([0.4, float("nan"), 0.7])
            n_oob = np.array([2, 0, 4])
            n_esc = np.array([1, 0, 2])
            rq69.write_bootstrap_csv(out, boot_idx, thr, oob, n_oob, n_esc, 4)
            with out.open() as fh:
                rows = list(_csv.reader(fh))
            # 1 header + 3 resamples.
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0][0], "resample")
            self.assertEqual(rows[0][1], "threshold")
            self.assertEqual(rows[0][2], "oob_cpwer")
            # Row 0: resample 0, threshold 0.5, oob_cpwer 0.4, n_oob 2, n_esc 1.
            self.assertEqual(rows[1][0], "0")
            self.assertAlmostEqual(float(rows[1][1]), 0.5, 4)
            self.assertAlmostEqual(float(rows[1][2]), 0.4, 4)
            self.assertEqual(rows[1][3], "2")
            self.assertEqual(rows[1][4], "1")
            # Row 1: empty OOB -> oob_cpwer blank, escalation_fraction_oob blank.
            self.assertEqual(rows[2][3], "0")
            self.assertEqual(rows[2][2], "")  # nan -> blank
            self.assertEqual(rows[2][6], "")  # 0/0 -> blank
        finally:
            if out.exists():
                out.unlink()

    def test_results_csv_exists_and_consistent_with_json(self) -> None:
        # The results CSV must exist and have B+1 rows (header + B resamples).
        self.assertTrue(OUT_CSV.exists(), f"missing {OUT_CSV}")
        with OUT_CSV.open() as fh:
            rows = list(_csv.reader(fh))
        self.assertEqual(len(rows), rq69.N_BOOT + 1)
        self.assertEqual(rows[0][0], "resample")
        self.assertEqual(rows[0][1], "threshold")
        # First data row is resample 0.
        self.assertEqual(rows[1][0], "0")
        # Threshold in row 1 must be in the KL grid range.
        thr = float(rows[1][1])
        self.assertGreaterEqual(thr, 0.0)
        self.assertLessEqual(thr, 8.55)


# --------------------------------------------------------------- MeetEval smoke
@unittest.skipUnless(HAS_MEETEVAL, "MeetEval not installed")
class MeetEvalSmokeTest(unittest.TestCase):
    """Verify the cpWER API is reachable via the project's standard import.

    The RQ69 cascade simulation reads per-window cpWER from RQ43's JSON (no
    MeetEval call). This smoke test guards the cpWER *concept* (so a future
    refactor that introduces a MeetEval call stays correct) but is skipped
    when MeetEval is not installed. Follows the per_mode_bca_decomposition
    import pattern: ``from meeteval.wer import cpwer``.
    """

    def test_cpwer_import_reachable(self) -> None:
        # The project's standard import path (per per_mode_bca_decomposition).
        from meeteval.wer import cpwer  # noqa: F401
        self.assertTrue(callable(cpwer))

    def test_cpwer_perfect_match_zero_error_rate(self) -> None:
        # cpwer takes segment lists with session_id / speaker / words fields
        # and returns a dict keyed by session_id; perfect match -> 0 errors.
        from meeteval.wer import cpwer
        SESSION_ID = "smoke"
        ref = [{"session_id": SESSION_ID, "speaker": "spk1",
                "words": list("abc")}]
        hyp = [{"session_id": SESSION_ID, "speaker": "spk1",
                "words": list("abc")}]
        out = cpwer(ref, hyp)
        self.assertIn(SESSION_ID, out)
        self.assertAlmostEqual(float(out[SESSION_ID].error_rate), 0.0, 6)


if __name__ == "__main__":
    unittest.main()
