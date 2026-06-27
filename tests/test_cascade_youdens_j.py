"""Tests for RQ59: cascade with Youden's J calibration (experimental/frontier).

Pins the pure helpers: ``norm_ppf`` (Acklam inverse normal), ``count_modes``
(RQ48 re-export), ``cascade_cpwer_at_threshold`` / ``cascade_compute_at_threshold``
/ ``cascade_oob_cpwer`` (the RQ43 cascade simulation held fixed), the vectorised
``bootstrap_youdens_j_cascade`` (proved equivalent to RQ48's per-call
``calibrate_youdens_j``), ``jackknife_acceleration``, and ``bca_ci``. Also
smoke-tests the in-sample calibration on the real 77-window AISHELL-4 corpus:
RQ43's original-rule cascade @ KL=3.30 reproduces 0.888947, the Youden's J
label counts are 37/40, and the central RQ59 finding -- that Youden's J
collapses to the SAME aggressive operating point as F1 (KL=0.01, 83.1%
escalation) -- is pinned.

No Whisper / no audio needed. numpy + stdlib only.
"""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

# The RQ59 analysis script lives in results/frontier/ as a standalone module
# (no src. package), mirroring the RQ44/RQ48/RQ54 test pattern. The script
# itself adds RQ48 + RQ44 dirs to sys.path and imports them.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_DIR = _PROJECT_ROOT / "results" / "frontier" / "cascade_youdens_j"
sys.path.insert(0, str(_SCRIPT_DIR))

import cascade_youdens_j_analysis as rq59  # noqa: E402  (path-injected import)

# RQ48's module is needed for the Youden's-J-equivalence cross-check.
_RQ48_DIR = _PROJECT_ROOT / "results" / "frontier" / "calibration_rule_comparison"
sys.path.insert(0, str(_RQ48_DIR))
import calibration_rule_analysis as rq48  # noqa: E402  (path-injected import)

RQ43_JSON = (
    _PROJECT_ROOT
    / "results"
    / "frontier"
    / "three_tier_cascade"
    / "three_tier_cascade_results.json"
)


# --------------------------------------------------------------- constants
class TestConstants(unittest.TestCase):
    def test_bootstrap_conventions(self) -> None:
        self.assertEqual(rq59.N_BOOT, 10000)
        self.assertEqual(rq59.SEED, 42)
        self.assertEqual(rq59.MIN_MODE_FRACTION, 0.05)
        self.assertEqual(rq59.ALPHA, 0.05)

    def test_kl_grid_covers_rq43_kl_range(self) -> None:
        # RQ43 KL range is [0.0, 8.5255]; grid must span it at 0.01 step.
        self.assertEqual(rq59.KL_THRESHOLD_GRID[0], 0.0)
        self.assertEqual(rq59.KL_THRESHOLD_GRID[-1], 8.55)
        self.assertEqual(len(rq59.KL_THRESHOLD_GRID), 856)
        # step is exactly 0.01
        for i in range(1, 10):
            self.assertAlmostEqual(
                rq59.KL_THRESHOLD_GRID[i] - rq59.KL_THRESHOLD_GRID[i - 1], 0.01, 8)

    def test_rq43_anchors_match_task_brief(self) -> None:
        self.assertAlmostEqual(rq59.RQ43_CASCADE_CPWER, 0.888947, 6)
        self.assertAlmostEqual(rq59.RQ43_BASELINE_CPWER, 1.590909, 6)
        self.assertAlmostEqual(rq59.RQ43_BASE_RATIO, 0.428031, 6)
        self.assertEqual(rq59.RQ43_KL_THRESHOLD, 3.30)

    def test_rq46_ci_width_anchor(self) -> None:
        # H59c comparison anchor: 1.016343 - 0.767399 = 0.248944 -> 0.2489 (4 dp).
        self.assertAlmostEqual(rq59.RQ46_CI_LO, 0.767399, 6)
        self.assertAlmostEqual(rq59.RQ46_CI_HI, 1.016343, 6)
        self.assertAlmostEqual(rq59.RQ46_CI_WIDTH, 0.2489, 4)
        self.assertEqual(rq59.H59C_MAX_WIDTH, 0.2489)

    def test_rq54_f1_reference_anchors(self) -> None:
        # H59a anchor: F1 escalation 0.831169 (83.1%).
        self.assertAlmostEqual(rq59.RQ54_F1_ESCALATION, 0.831169, 6)
        self.assertAlmostEqual(rq59.RQ54_F1_OOB_MEDIAN_CPWER, 0.779853, 6)
        self.assertAlmostEqual(rq59.RQ54_F1_BCA_WIDTH, 0.248072, 6)
        self.assertEqual(rq59.RQ54_F1_MODES_KL, 1)
        self.assertEqual(rq59.RQ48_YOUDENS_J_MODES_LANGID, 3)

    def test_hypothesis_kill_thresholds(self) -> None:
        self.assertEqual(rq59.H59A_MAX_ESCALATION, 0.83)
        self.assertEqual(rq59.H59B_MAX_CPWER, 0.889)
        self.assertEqual(rq59.H59C_MAX_WIDTH, rq59.RQ46_CI_WIDTH)


# --------------------------------------------------------------- inverse normal CDF
class TestNormPpf(unittest.TestCase):
    def test_median_is_zero(self) -> None:
        self.assertAlmostEqual(rq59.norm_ppf(0.5), 0.0, 6)

    def test_known_quantiles(self) -> None:
        self.assertAlmostEqual(rq59.norm_ppf(0.975), 1.959964, 5)
        self.assertAlmostEqual(rq59.norm_ppf(0.025), -1.959964, 5)
        self.assertAlmostEqual(rq59.norm_ppf(0.8413447), 1.0, 4)  # Phi(1)=0.8413

    def test_symmetry(self) -> None:
        for p in (0.1, 0.25, 0.4, 0.6, 0.75, 0.9):
            self.assertAlmostEqual(rq59.norm_ppf(p), -rq59.norm_ppf(1.0 - p), 6)

    def test_monotonic_increasing(self) -> None:
        ps = [0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99]
        xs = [rq59.norm_ppf(p) for p in ps]
        for a, b in zip(xs, xs[1:]):
            self.assertLess(a, b)

    def test_endpoints_infinite(self) -> None:
        self.assertEqual(rq59.norm_ppf(0.0), float("-inf"))
        self.assertEqual(rq59.norm_ppf(1.0), float("inf"))
        self.assertEqual(rq59.norm_ppf(-0.1), float("-inf"))
        self.assertEqual(rq59.norm_ppf(1.1), float("inf"))

    def test_accuracy_against_erf(self) -> None:
        # norm_ppf then forward-Phi (0.5*erfc(-x/sqrt2)) should recover p.
        for p in (0.001, 0.05, 0.3, 0.5, 0.7, 0.95, 0.999):
            x = rq59.norm_ppf(p)
            recovered = 0.5 * math.erfc(-x / math.sqrt(2.0))
            self.assertAlmostEqual(recovered, p, 7)

    def test_norm_cdf_roundtrip(self) -> None:
        # Forward CDF of a few z-scores matches math.erf-based Phi.
        for x in (-2.0, -0.5, 0.0, 0.5, 2.0):
            expected = 0.5 * math.erfc(-x / math.sqrt(2.0))
            self.assertAlmostEqual(rq59.norm_cdf(x), expected, 9)


# --------------------------------------------------------------- Youden's J calibration on KL
class TestYoudensJCalibrationKL(unittest.TestCase):
    def test_youdens_j_is_rq48_reference(self) -> None:
        # RQ59 re-uses RQ48's calibrate_youdens_j verbatim (only the detector
        # changes).
        self.assertIs(rq59.calibrate_youdens_j, rq48.calibrate_youdens_j)

    def test_separable_case_maximises_j(self) -> None:
        # negs 0/1/2, pos 8/9. J=1 for any t in (2, 8]; tie-break -> lowest = 2.01.
        grid = [0.0, 0.5, 1.0, 1.5, 2.0, 2.01, 5.0, 8.0, 8.01, 10.0]
        scores = np.array([0.0, 1.0, 2.0, 8.0, 9.0])
        labels = np.array([0, 0, 0, 1, 1])
        out = rq59.calibrate_youdens_j(scores, labels, grid=grid)
        self.assertAlmostEqual(out["threshold"], 2.01, 6)
        self.assertEqual(out["sensitivity"], 1.0)
        self.assertEqual(out["specificity"], 1.0)
        self.assertAlmostEqual(out["youdens_j"], 1.0, 6)

    def test_j_value_formula(self) -> None:
        # J = sensitivity + specificity - 1, pinned using out's own values.
        scores = np.array([0.0, 0.5, 1.0, 1.5])
        labels = np.array([0, 0, 1, 1])
        out = rq59.calibrate_youdens_j(scores, labels, grid=[0.0, 0.5, 1.0, 1.01])
        # At t=1.0: TP=2, FP=0, TN=2, FN=0 -> sens=1, spec=1, J=1 (the max).
        self.assertAlmostEqual(out["threshold"], 1.0, 6)
        sens = out["sensitivity"]
        spec = out["specificity"]
        expected_j = sens + spec - 1.0
        self.assertAlmostEqual(out["youdens_j"], expected_j, 6)
        self.assertAlmostEqual(out["youdens_j"], 1.0, 6)

    def test_tie_break_lowest_threshold(self) -> None:
        scores = np.array([0.0, 1.0, 5.0, 6.0])
        labels = np.array([0, 0, 1, 1])
        out = rq59.calibrate_youdens_j(scores, labels, grid=[1.0, 1.01, 5.0, 5.01])
        # J=1 for t in (1.0, 5.0]; lowest grid point achieving it = 1.01.
        self.assertAlmostEqual(out["threshold"], 1.01, 6)
        self.assertAlmostEqual(out["youdens_j"], 1.0, 6)

    def test_empty_positives_j_zero_at_highest_threshold(self) -> None:
        # No positives -> sens=0; J = spec - 1 <= 0, maximised at spec=1 (no
        # flags) which is the highest grid threshold.
        scores = np.array([0.0, 0.5, 1.0])
        labels = np.array([0, 0, 0])
        out = rq59.calibrate_youdens_j(scores, labels, grid=[0.0, 0.5, 1.01])
        self.assertEqual(out["sensitivity"], 0.0)
        self.assertEqual(out["tp"], 0)
        self.assertEqual(out["fn"], 0)
        self.assertAlmostEqual(out["youdens_j"], 0.0, 6)
        self.assertAlmostEqual(out["threshold"], 1.01, 6)  # highest = no flags

    def test_in_sample_threshold_in_kl_range(self) -> None:
        w = rq59.load_rq43_per_window()
        labels = (w["tiny"] > rq59.CATASTROPHIC_CPWER).astype(int)
        cal = rq59.calibrate_youdens_j(w["kl"], labels, grid=rq59.KL_THRESHOLD_GRID)
        self.assertGreaterEqual(cal["threshold"], 0.0)
        self.assertLessEqual(cal["threshold"], 8.55)
        self.assertGreaterEqual(cal["sensitivity"], 0.0)
        self.assertLessEqual(cal["sensitivity"], 1.0)
        self.assertGreaterEqual(cal["specificity"], 0.0)
        self.assertLessEqual(cal["specificity"], 1.0)
        # J must be > -1 (always true) and finite.
        self.assertTrue(np.isfinite(cal["youdens_j"]))
        self.assertGreaterEqual(cal["youdens_j"], -1.0)

    def test_in_sample_collapses_to_same_point_as_f1(self) -> None:
        # CENTRAL RQ59 FINDING: on the real KL detector, Youden's J picks the
        # SAME operating point as F1 (threshold 0.01, sens=1.0, spec=0.325),
        # because the KL ROC is flat-topped: raising the threshold above 0.01
        # loses hallucinated windows (sens falls) without gaining specificity
        # (clean high-KL windows stay flagged). J is maximised at 0.325 across
        # [0.01, ~2.98]; the lowest-threshold tie-break picks 0.01.
        w = rq59.load_rq43_per_window()
        labels = (w["tiny"] > rq59.CATASTROPHIC_CPWER).astype(int)
        cal_j = rq59.calibrate_youdens_j(w["kl"], labels, grid=rq59.KL_THRESHOLD_GRID)
        cal_f1 = rq48.calibrate_f1(w["kl"], labels, grid=rq59.KL_THRESHOLD_GRID)
        self.assertAlmostEqual(cal_j["threshold"], cal_f1["threshold"], 6)
        self.assertAlmostEqual(cal_j["threshold"], 0.01, 6)
        self.assertEqual(cal_j["sensitivity"], cal_f1["sensitivity"])
        self.assertEqual(cal_j["specificity"], cal_f1["specificity"])
        self.assertEqual(cal_j["tp"], cal_f1["tp"])
        self.assertEqual(cal_j["fp"], cal_f1["fp"])
        self.assertAlmostEqual(cal_j["youdens_j"], 0.325, 3)

    def test_in_sample_escalation_at_least_83_percent(self) -> None:
        # H59a kill condition: in-sample escalation fraction >= 0.83.
        w = rq59.load_rq43_per_window()
        labels = (w["tiny"] > rq59.CATASTROPHIC_CPWER).astype(int)
        cal = rq59.calibrate_youdens_j(w["kl"], labels, grid=rq59.KL_THRESHOLD_GRID)
        frac = float(np.mean(w["kl"] >= cal["threshold"] - rq59.EPS))
        self.assertGreaterEqual(frac, rq59.H59A_MAX_ESCALATION)
        self.assertAlmostEqual(frac, rq59.RQ54_F1_ESCALATION, 4)


# --------------------------------------------------------------- cascade simulation
class TestCascadeSimulation(unittest.TestCase):
    def test_no_escalation_equals_tiny_mean(self) -> None:
        tiny = np.array([1.0, 2.0, 3.0, 4.0])
        base = np.array([0.5, 1.0, 1.5, 2.0])
        kl = np.array([0.0, 0.1, 0.2, 0.3])
        # threshold above all KL -> nothing escalated -> tiny mean.
        cp = rq59.cascade_cpwer_at_threshold(tiny, base, kl, 10.0)
        self.assertAlmostEqual(cp, tiny.mean(), 6)

    def test_all_escalation_equals_base_mean(self) -> None:
        tiny = np.array([1.0, 2.0, 3.0, 4.0])
        base = np.array([0.5, 1.0, 1.5, 2.0])
        kl = np.array([5.0, 6.0, 7.0, 8.0])
        # threshold below all KL -> all escalated -> base mean.
        cp = rq59.cascade_cpwer_at_threshold(tiny, base, kl, 0.0)
        self.assertAlmostEqual(cp, base.mean(), 6)

    def test_partial_escalation_mixed_mean(self) -> None:
        tiny = np.array([1.0, 2.0, 3.0, 4.0])
        base = np.array([0.5, 1.0, 1.5, 2.0])
        kl = np.array([0.0, 1.0, 2.0, 3.0])
        # threshold 1.5 -> escalate kl>=1.5 (windows 2,3).
        # selected = [tiny0, tiny1, base2, base3] = [1.0, 2.0, 1.5, 2.0] mean=1.625
        cp = rq59.cascade_cpwer_at_threshold(tiny, base, kl, 1.5)
        self.assertAlmostEqual(cp, np.mean([1.0, 2.0, 1.5, 2.0]), 6)

    def test_empty_returns_zero(self) -> None:
        cp = rq59.cascade_cpwer_at_threshold(np.array([]), np.array([]),
                                             np.array([]), 1.0)
        self.assertEqual(cp, 0.0)

    def test_compute_formula(self) -> None:
        kl = np.array([0.0, 1.0, 2.0, 3.0])  # 2 of 4 escalated at t=1.5 -> f=0.5
        comp = rq59.cascade_compute_at_threshold(kl, 1.5)
        self.assertAlmostEqual(comp, 1.0 * 0.5 + 1.93 * 0.5, 6)

    def test_compute_no_escalation_is_tiny(self) -> None:
        kl = np.array([0.0, 0.1, 0.2])
        self.assertAlmostEqual(rq59.cascade_compute_at_threshold(kl, 10.0), 1.0, 6)

    def test_compute_all_escalation_is_base(self) -> None:
        kl = np.array([5.0, 6.0, 7.0])
        self.assertAlmostEqual(rq59.cascade_compute_at_threshold(kl, 0.0), 1.93, 6)

    def test_reproduces_rq43_at_kl_3_30(self) -> None:
        # Controlled-comparison anchor: RQ43's cascade @ KL=3.30 = 0.888947.
        w = rq59.load_rq43_per_window()
        cp = rq59.cascade_cpwer_at_threshold(w["tiny"], w["base"], w["kl"], 3.30)
        self.assertAlmostEqual(cp, rq59.RQ43_CASCADE_CPWER, 4)

    def test_base_ratio_matches_rq43(self) -> None:
        # base = tiny * 0.428031 (RQ43's separated model_scale ratio).
        w = rq59.load_rq43_per_window()
        ratio = float(np.mean(w["base"] / w["tiny"]))
        self.assertAlmostEqual(ratio, rq59.RQ43_BASE_RATIO, 4)


# --------------------------------------------------------------- OOB cascade cpWER
class TestCascadeOOB(unittest.TestCase):
    def test_oob_excludes_in_bag(self) -> None:
        tiny = np.array([1.0, 2.0, 3.0, 4.0])
        base = np.array([0.5, 1.0, 1.5, 2.0])
        kl = np.array([0.0, 1.0, 2.0, 3.0])
        # in_bag = {0, 1} -> OOB = {2, 3}; threshold 10 -> none escalated.
        out = rq59.cascade_oob_cpwer(tiny, base, kl, 10.0, np.array([0, 1]))
        self.assertEqual(out["n_oob"], 2)
        self.assertEqual(out["n_escalated"], 0)
        self.assertAlmostEqual(out["cpwer"], np.mean([3.0, 4.0]), 6)

    def test_oob_escalation_uses_threshold(self) -> None:
        tiny = np.array([1.0, 2.0, 3.0, 4.0])
        base = np.array([0.5, 1.0, 1.5, 2.0])
        kl = np.array([0.0, 1.0, 2.0, 3.0])
        # in_bag = {0} -> OOB = {1,2,3}; threshold 2.5 -> escalate window 3 only.
        out = rq59.cascade_oob_cpwer(tiny, base, kl, 2.5, np.array([0]))
        self.assertEqual(out["n_oob"], 3)
        self.assertEqual(out["n_escalated"], 1)
        # selected = [tiny1, tiny2, base3] = [2.0, 3.0, 2.0] mean = 2.3333
        self.assertAlmostEqual(out["cpwer"], np.mean([2.0, 3.0, 2.0]), 6)

    def test_oob_empty_returns_nan(self) -> None:
        tiny = np.array([1.0, 2.0])
        base = np.array([0.5, 1.0])
        kl = np.array([0.0, 1.0])
        # in_bag = {0, 1} -> OOB empty.
        out = rq59.cascade_oob_cpwer(tiny, base, kl, 1.0, np.array([0, 1, 0, 1]))
        self.assertEqual(out["n_oob"], 0)
        self.assertTrue(math.isnan(out["cpwer"]))

    def test_oob_in_bag_duplicates_dont_double_count(self) -> None:
        tiny = np.array([1.0, 2.0, 3.0])
        base = np.array([0.5, 1.0, 1.5])
        kl = np.array([0.0, 1.0, 2.0])
        # in_bag indices [0, 0, 0] -> unique in_bag = {0}; OOB = {1, 2}.
        out = rq59.cascade_oob_cpwer(tiny, base, kl, 10.0, np.array([0, 0, 0]))
        self.assertEqual(out["n_oob"], 2)


# --------------------------------------------------------------- bootstrap Youden's J cascade
class TestBootstrapYoudensJCascade(unittest.TestCase):
    def test_deterministic_with_seed(self) -> None:
        tiny = np.array([1.0, 2.0, 3.0, 4.0, 1.5, 2.5])
        base = tiny * 0.5
        kl = np.array([0.0, 0.5, 1.0, 1.5, 8.0, 8.5])
        labels = (tiny > 1.2).astype(int)
        a = rq59.bootstrap_youdens_j_cascade(tiny, base, kl, labels, n_boot=20, seed=42)
        b = rq59.bootstrap_youdens_j_cascade(tiny, base, kl, labels, n_boot=20, seed=42)
        np.testing.assert_array_equal(a["boot_idx"], b["boot_idx"])
        np.testing.assert_array_equal(a["thresholds"], b["thresholds"])
        np.testing.assert_array_equal(a["oob_cpwer"], b["oob_cpwer"])

    def test_shapes(self) -> None:
        n, n_boot = 7, 12
        rng = np.random.default_rng(0)
        tiny = rng.uniform(0.5, 2.0, n)
        base = tiny * 0.4
        kl = rng.uniform(0.0, 8.0, n)
        labels = (tiny > 1.0).astype(int)
        out = rq59.bootstrap_youdens_j_cascade(tiny, base, kl, labels, n_boot=n_boot, seed=1)
        self.assertEqual(out["boot_idx"].shape, (n_boot, n))
        self.assertEqual(out["thresholds"].shape, (n_boot,))
        self.assertEqual(out["oob_cpwer"].shape, (n_boot,))
        self.assertEqual(out["n_oob"].shape, (n_boot,))

    def test_thresholds_within_grid(self) -> None:
        rng = np.random.default_rng(3)
        n = 10
        tiny = rng.uniform(0.5, 2.0, n)
        base = tiny * 0.4
        kl = rng.uniform(0.0, 8.5, n)
        labels = (tiny > 1.0).astype(int)
        out = rq59.bootstrap_youdens_j_cascade(tiny, base, kl, labels, n_boot=30, seed=7)
        self.assertTrue(np.all(out["thresholds"] >= 0.0))
        self.assertTrue(np.all(out["thresholds"] <= 8.55))

    def test_oob_size_positive_and_bounded(self) -> None:
        # OOB size is between 0 and n; mean ~ n*(1-(1-1/n)^n) ~ 0.368*n.
        rng = np.random.default_rng(5)
        n = 50
        tiny = rng.uniform(0.5, 2.0, n)
        base = tiny * 0.4
        kl = rng.uniform(0.0, 8.0, n)
        labels = (tiny > 1.0).astype(int)
        out = rq59.bootstrap_youdens_j_cascade(tiny, base, kl, labels, n_boot=200, seed=11)
        self.assertTrue(np.all(out["n_oob"] >= 0))
        self.assertTrue(np.all(out["n_oob"] <= n))
        self.assertGreater(np.mean(out["n_oob"]), n * 0.25)

    def test_vectorised_matches_calibrate_youdens_j(self) -> None:
        # The vectorised bootstrap's per-resample threshold must equal RQ48's
        # calibrate_youdens_j applied to that resample's in-bag data (lowest-t
        # tie-break, >= - EPS flagging, RQ48's empty-class convention).
        rng = np.random.default_rng(0)
        n = 12
        tiny = rng.uniform(0.5, 2.0, n)
        base = tiny * 0.4
        kl = rng.uniform(0.0, 8.5, n)
        labels = (tiny > 1.0).astype(int)
        out = rq59.bootstrap_youdens_j_cascade(tiny, base, kl, labels, n_boot=8, seed=99)
        for b in range(8):
            idx = out["boot_idx"][b]
            cal = rq48.calibrate_youdens_j(kl[idx], labels[idx], grid=rq59.KL_THRESHOLD_GRID)
            self.assertAlmostEqual(
                float(out["thresholds"][b]), cal["threshold"], 6,
                msg=(f"resample {b}: vectorised {out['thresholds'][b]} vs "
                     f"calibrate_youdens_j {cal['threshold']}"))

    def test_oob_cpwer_within_tiny_base_range(self) -> None:
        # OOB cpWER must lie in [min(base), max(tiny)] (base<=tiny here).
        rng = np.random.default_rng(2)
        n = 15
        tiny = rng.uniform(1.0, 3.0, n)
        base = tiny * 0.4  # base < tiny always
        kl = rng.uniform(0.0, 8.0, n)
        labels = (tiny > 1.5).astype(int)
        out = rq59.bootstrap_youdens_j_cascade(tiny, base, kl, labels, n_boot=50, seed=4)
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
        out = rq59.bootstrap_youdens_j_cascade(tiny, base, kl, labels, n_boot=6, seed=5)
        for b in range(6):
            if out["n_oob"][b] == 0:
                self.assertTrue(math.isnan(float(out["oob_cpwer"][b])))
                continue
            oob = rq59.cascade_oob_cpwer(
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
        a, loo = rq59.jackknife_acceleration(tiny, base, kl, labels,
                                             grid=rq59.KL_THRESHOLD_GRID)
        self.assertEqual(loo.shape, (n,))
        self.assertTrue(np.all(np.isfinite(loo)))
        self.assertTrue(np.isfinite(a))

    def test_zero_variation_when_identical(self) -> None:
        # All windows identical -> every LOO fit gives the same theta -> a = 0.
        tiny = np.array([1.0] * 6)
        base = np.array([0.4] * 6)
        kl = np.array([2.0] * 6)
        labels = np.array([1, 1, 1, 0, 0, 0])  # need both classes for J
        # With identical kl the J threshold is the lowest grid point (0.0);
        # all LOO fits identical -> theta_loo constant -> a = 0.
        a, loo = rq59.jackknife_acceleration(tiny, base, kl, labels,
                                             grid=rq59.KL_THRESHOLD_GRID)
        self.assertAlmostEqual(a, 0.0, 9)

    def test_acceleration_finite_on_real_data(self) -> None:
        w = rq59.load_rq43_per_window()
        labels = (w["tiny"] > rq59.CATASTROPHIC_CPWER).astype(int)
        a, loo = rq59.jackknife_acceleration(w["tiny"], w["base"], w["kl"], labels,
                                             grid=rq59.KL_THRESHOLD_GRID)
        self.assertEqual(loo.shape, (77,))
        self.assertTrue(np.all(np.isfinite(loo)))
        self.assertTrue(np.isfinite(a))
        self.assertLess(abs(a), 1.0)  # acceleration is typically small


# --------------------------------------------------------------- BCa CI
class TestBCa(unittest.TestCase):
    def test_equals_percentile_when_no_bias_no_accel(self) -> None:
        # z0 = 0 (theta_hat = median) and accel = 0 -> BCa == percentile CI.
        boot = np.arange(100, dtype=float)  # 0..99; 50 values < 49.5
        theta_hat = 49.5
        bca = rq59.bca_ci(theta_hat, boot, accel=0.0, alpha=0.05)
        self.assertEqual(bca["method"], "bca")
        lo = float(np.percentile(boot, 2.5))
        hi = float(np.percentile(boot, 97.5))
        self.assertAlmostEqual(bca["lo"], lo, 4)
        self.assertAlmostEqual(bca["hi"], hi, 4)
        self.assertAlmostEqual(bca["z0"], 0.0, 4)

    def test_bias_shifts_ci_right_when_theta_hat_high(self) -> None:
        boot = np.linspace(0.0, 100.0, 101)
        # theta_hat well above the bootstrap median -> z0 > 0 -> CI shifts up.
        bca_low = rq59.bca_ci(50.0, boot, accel=0.0)
        bca_high = rq59.bca_ci(95.0, boot, accel=0.0)
        self.assertGreater(bca_high["lo"], bca_low["lo"])
        self.assertGreater(bca_high["hi"], bca_low["hi"])
        self.assertGreater(bca_high["z0"], bca_low["z0"])

    def test_width_is_hi_minus_lo(self) -> None:
        rng = np.random.default_rng(0)
        boot = rng.normal(1.0, 0.2, 500)
        bca = rq59.bca_ci(1.0, boot, accel=0.0)
        self.assertAlmostEqual(bca["hi"] - bca["lo"],
                               bca["hi"] - bca["lo"], 6)

    def test_accel_finite_changes_ci(self) -> None:
        # A non-zero acceleration should (generically) move the CI vs accel=0.
        boot = np.linspace(0.0, 100.0, 101)
        bca0 = rq59.bca_ci(50.0, boot, accel=0.0)
        bca_a = rq59.bca_ci(50.0, boot, accel=0.1)
        self.assertEqual(bca0["method"], "bca")
        self.assertEqual(bca_a["method"], "bca")
        # With acceleration the adjusted percentiles differ from 2.5/97.5.
        self.assertNotAlmostEqual(bca_a["alpha1"], 0.025, 4)

    def test_degenerate_constant_boot(self) -> None:
        # All bootstrap samples equal theta_hat -> CI collapses to a point.
        boot = np.full(100, 0.7)
        bca = rq59.bca_ci(0.7, boot, accel=0.0)
        self.assertEqual(bca["method"], "bca")
        self.assertAlmostEqual(bca["lo"], 0.7, 6)
        self.assertAlmostEqual(bca["hi"], 0.7, 6)
        self.assertAlmostEqual(bca["median"], 0.7, 6)

    def test_nan_samples_dropped(self) -> None:
        boot = np.array([1.0, 2.0, np.nan, 3.0, np.nan, 4.0])
        bca = rq59.bca_ci(2.5, boot, accel=0.0)
        self.assertEqual(bca["n_valid"], 4)
        self.assertTrue(np.isfinite(bca["lo"]))
        self.assertTrue(np.isfinite(bca["hi"]))

    def test_empty_boot_returns_nan(self) -> None:
        bca = rq59.bca_ci(1.0, np.array([]), accel=0.0)
        self.assertEqual(bca["method"], "empty")
        self.assertTrue(math.isnan(bca["lo"]))
        self.assertTrue(math.isnan(bca["hi"]))

    def test_ci_brackets_median(self) -> None:
        rng = np.random.default_rng(1)
        boot = rng.normal(0.0, 1.0, 1000)
        bca = rq59.bca_ci(0.0, boot, accel=0.05)
        self.assertLessEqual(bca["lo"], bca["median"] + 1e-9)
        self.assertGreaterEqual(bca["hi"], bca["median"] - 1e-9)


# --------------------------------------------------------------- mode count (RQ48 re-export)
class TestModeCount(unittest.TestCase):
    def test_single_mode(self) -> None:
        thr = np.array([1.0] * 80 + [2.0] * 20)  # 2.0 at 20% is also a mode
        m = rq59.count_modes(thr, 0.05)
        self.assertEqual(m["n_modes"], 2)

    def test_two_modes(self) -> None:
        thr = np.array([0.5] * 60 + [1.5] * 40)
        m = rq59.count_modes(thr, 0.05)
        self.assertEqual(m["n_modes"], 2)
        # sorted by descending count
        self.assertAlmostEqual(m["modes"][0]["threshold"], 0.5, 6)
        self.assertAlmostEqual(m["modes"][1]["threshold"], 1.5, 6)

    def test_sub_5pct_excluded(self) -> None:
        thr = np.array([1.0] * 90 + [2.0] * 4 + [3.0] * 6)  # 2.0 at 4% excluded
        m = rq59.count_modes(thr, 0.05)
        thresholds = {md["threshold"] for md in m["modes"]}
        self.assertIn(1.0, thresholds)
        self.assertIn(3.0, thresholds)
        self.assertNotIn(2.0, thresholds)

    def test_empty(self) -> None:
        m = rq59.count_modes(np.array([]), 0.05)
        self.assertEqual(m["n_modes"], 0)
        self.assertEqual(m["n_unique"], 0)

    def test_matches_rq48_count_modes(self) -> None:
        # rq59.count_modes IS rq48.count_modes (re-exported).
        self.assertIs(rq59.count_modes, rq48.count_modes)
        thr = np.array([0.38] * 60 + [0.01] * 30 + [0.95] * 10)
        self.assertEqual(rq59.count_modes(thr, 0.05)["n_modes"], 3)


# --------------------------------------------------------------- end-to-end smoke
class TestEndToEnd(unittest.TestCase):
    def test_load_rq43_per_window(self) -> None:
        w = rq59.load_rq43_per_window()
        self.assertEqual(len(w["tiny"]), 77)
        self.assertEqual(len(w["base"]), 77)
        self.assertEqual(len(w["kl"]), 77)
        self.assertAlmostEqual(float(w["tiny"].mean()), rq59.RQ43_BASELINE_CPWER, 4)

    def test_label_counts_37_40(self) -> None:
        w = rq59.load_rq43_per_window()
        labels = (w["tiny"] > rq59.CATASTROPHIC_CPWER).astype(int)
        self.assertEqual(int(labels.sum()), 37)
        self.assertEqual(int((labels == 0).sum()), 40)

    def test_rq43_reproduction_strict_and_ge_match(self) -> None:
        # >= - EPS and strict > give the same cascade cpWER at KL=3.30 here
        # (no window has KL exactly 3.30), reproducing RQ43's 0.888947.
        w = rq59.load_rq43_per_window()
        cp_ge = rq59.cascade_cpwer_at_threshold(w["tiny"], w["base"], w["kl"], 3.30)
        cp_strict = float(np.mean(np.where(w["kl"] > 3.30, w["base"], w["tiny"])))
        self.assertAlmostEqual(cp_ge, cp_strict, 6)
        self.assertAlmostEqual(cp_ge, rq59.RQ43_CASCADE_CPWER, 4)

    def test_kl_detector_roc_properties(self) -> None:
        # Pins the data geometry that drives the central finding: all
        # hallucinated windows have KL >= ~2.98, but clean windows span the
        # full KL range [0, 8.53] (13 clean windows have KL == 0). This is why
        # Youden's J cannot improve specificity by raising the threshold: clean
        # high-KL windows stay flagged.
        w = rq59.load_rq43_per_window()
        labels = (w["tiny"] > rq59.CATASTROPHIC_CPWER).astype(int)
        hall_kl = w["kl"][labels == 1]
        clean_kl = w["kl"][labels == 0]
        self.assertGreater(float(hall_kl.min()), 2.9)   # hall KL floor ~ 2.98
        self.assertLess(float(hall_kl.min()), 3.0)
        self.assertAlmostEqual(float(clean_kl.min()), 0.0, 6)  # 13 clean at KL=0
        self.assertGreater(float(clean_kl.max()), 8.0)  # clean high-KL tail
        self.assertEqual(int(((w["kl"] == 0) & (labels == 0)).sum()), 13)

    def test_small_bootstrap_end_to_end(self) -> None:
        # A tiny bootstrap on the real data: runs fast, produces valid output.
        w = rq59.load_rq43_per_window()
        labels = (w["tiny"] > rq59.CATASTROPHIC_CPWER).astype(int)
        out = rq59.bootstrap_youdens_j_cascade(w["tiny"], w["base"], w["kl"], labels,
                                               grid=rq59.KL_THRESHOLD_GRID,
                                               n_boot=30, seed=42)
        self.assertEqual(out["thresholds"].shape, (30,))
        valid = out["oob_cpwer"][~np.isnan(out["oob_cpwer"])]
        self.assertGreater(len(valid), 0)
        # OOB cpWER is a mean of per-window cpWERs in [0, ~2.4].
        self.assertTrue(np.all(valid >= 0.0))
        self.assertTrue(np.all(valid < 3.0))

    def test_small_bca_end_to_end(self) -> None:
        w = rq59.load_rq43_per_window()
        labels = (w["tiny"] > rq59.CATASTROPHIC_CPWER).astype(int)
        out = rq59.bootstrap_youdens_j_cascade(w["tiny"], w["base"], w["kl"], labels,
                                               grid=rq59.KL_THRESHOLD_GRID,
                                               n_boot=200, seed=42)
        cal = rq59.calibrate_youdens_j(w["kl"], labels, grid=rq59.KL_THRESHOLD_GRID)
        theta_hat = rq59.cascade_cpwer_at_threshold(
            w["tiny"], w["base"], w["kl"], cal["threshold"])
        accel, _ = rq59.jackknife_acceleration(
            w["tiny"], w["base"], w["kl"], labels, grid=rq59.KL_THRESHOLD_GRID)
        bca = rq59.bca_ci(theta_hat, out["oob_cpwer"], accel)
        self.assertIn(bca["method"], ("bca", "percentile_fallback"))
        self.assertLessEqual(bca["lo"], bca["hi"] + 1e-9)
        self.assertTrue(np.isfinite(bca["lo"]))
        self.assertTrue(np.isfinite(bca["hi"]))

    def test_results_json_written_and_consistent(self) -> None:
        # The generated results JSON must exist, be labelled experimental/
        # frontier, and report the three hypothesis verdicts consistently with
        # the in-sample escalation / OOB median / BCa width.
        out_json = rq59.OUT_JSON
        self.assertTrue(out_json.exists(), f"missing {out_json}")
        data = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertEqual(data["label"], "experimental/frontier")
        self.assertEqual(data["n_windows"], 77)
        self.assertEqual(data["n_hallucinated"], 37)
        self.assertEqual(data["n_clean"], 40)
        # H59a: escalation fraction >= 0.83 -> KILLED (Youden's J == F1 point).
        frac = data["in_sample_youdens_j_calibration"]["escalation_fraction"]
        self.assertGreaterEqual(frac, rq59.H59A_MAX_ESCALATION)
        self.assertEqual(data["hypothesis_verdicts"]["H59a"]["supported"], False)
        # H59b: median cpWER <= 0.889 -> SUPPORTED.
        med = data["bootstrap_oob_cpwer_distribution"]["median"]
        self.assertLessEqual(med, rq59.H59B_MAX_CPWER)
        self.assertEqual(data["hypothesis_verdicts"]["H59b"]["supported"], True)
        # H59c: BCa width > 0.2489 -> KILLED.
        width = data["bca_ci"]["width"]
        self.assertGreater(width, rq59.H59C_MAX_WIDTH)
        self.assertEqual(data["hypothesis_verdicts"]["H59c"]["supported"], False)
        # BCa CI must bracket the OOB median.
        self.assertLessEqual(data["bca_ci"]["lo"], med + 1e-6)
        self.assertGreaterEqual(data["bca_ci"]["hi"], med - 1e-6)
        # Bootstrap arrays must have length N_BOOT.
        self.assertEqual(len(data["per_bootstrap"]["thresholds"]), rq59.N_BOOT)
        self.assertEqual(len(data["per_bootstrap"]["oob_cpwer"]), rq59.N_BOOT)
        self.assertEqual(len(data["per_bootstrap"]["n_oob"]), rq59.N_BOOT)

    def test_results_json_youdens_equals_f1_operating_point(self) -> None:
        # The headline RQ59 finding: Youden's J and F1 pick the SAME in-sample
        # operating point on the KL detector (threshold 0.01, 83.1% escalation,
        # cpWER 0.7775). Verified against RQ54's F1 JSON.
        data = json.loads(rq59.OUT_JSON.read_text(encoding="utf-8"))
        rq54_data = json.loads(rq59.RQ54_JSON.read_text(encoding="utf-8"))
        j_thr = data["in_sample_youdens_j_calibration"]["threshold"]
        f1_thr = rq54_data["in_sample_f1_calibration"]["threshold"]
        self.assertAlmostEqual(j_thr, f1_thr, 6)
        self.assertAlmostEqual(j_thr, 0.01, 6)
        j_frac = data["in_sample_youdens_j_calibration"]["escalation_fraction"]
        f1_frac = rq54_data["in_sample_f1_calibration"]["escalation_fraction"]
        self.assertAlmostEqual(j_frac, f1_frac, 6)
        j_cpwer = data["in_sample_youdens_j_calibration"]["cascade_cpwer"]
        f1_cpwer = rq54_data["in_sample_f1_calibration"]["cascade_cpwer"]
        self.assertAlmostEqual(j_cpwer, f1_cpwer, 6)


# --------------------------------------------------------------- CSV output
class TestCSVOutput(unittest.TestCase):
    def test_write_bootstrap_csv_header_and_rows(self) -> None:
        # Synthetic: 3 resamples, 4 windows. Verifies header, row count, and
        # that nan / empty-OOB rows are handled (blank oob_cpwer, blank esc frac).
        import csv as _csv
        tmp = _PROJECT_ROOT / "results" / "frontier" / "cascade_youdens_j"
        tmp.mkdir(parents=True, exist_ok=True)
        out = tmp / "_test_csv_tmp.csv"
        try:
            boot_idx = np.array([[0, 1, 2, 0], [0, 1, 0, 1], [0, 1, 2, 3]])
            thr = np.array([0.5, 1.0, 2.0])
            oob = np.array([0.4, float("nan"), 0.7])
            n_oob = np.array([2, 0, 4])
            n_esc = np.array([1, 0, 2])
            rq59.write_bootstrap_csv(out, boot_idx, thr, oob, n_oob, n_esc, 4)
            with out.open() as fh:
                rows = list(_csv.reader(fh))
            self.assertEqual(rows[0], ["resample", "threshold", "oob_cpwer",
                                       "n_oob", "n_escalated_oob", "oob_fraction",
                                       "escalation_fraction_oob"])
            self.assertEqual(len(rows), 4)  # header + 3
            self.assertEqual(rows[1][0], "0")
            self.assertEqual(rows[1][1], "0.5")
            self.assertEqual(rows[1][3], "2")
            # row 2 has empty OOB -> blank cpwer, blank esc fraction
            self.assertEqual(rows[2][2], "")
            self.assertEqual(rows[2][4], "0")
            self.assertEqual(rows[2][6], "")
        finally:
            if out.exists():
                out.unlink()

    def test_results_csv_exists_and_consistent_with_json(self) -> None:
        # The generated CSV must exist, have N_BOOT+1 lines, and its per-
        # resample thresholds / oob_cpwer must match the JSON per_bootstrap.
        import csv as _csv
        out_csv = rq59.OUT_CSV
        self.assertTrue(out_csv.exists(), f"missing {out_csv}")
        data = json.loads(rq59.OUT_JSON.read_text(encoding="utf-8"))
        json_thr = data["per_bootstrap"]["thresholds"]
        json_oob = data["per_bootstrap"]["oob_cpwer"]
        with out_csv.open() as fh:
            rows = list(_csv.reader(fh))
        self.assertEqual(rows[0][:5], ["resample", "threshold", "oob_cpwer",
                                       "n_oob", "n_escalated_oob"])
        # N_BOOT data rows + 1 header.
        self.assertEqual(len(rows), rq59.N_BOOT + 1)
        # spot-check first / last resample index and threshold match JSON.
        self.assertEqual(int(rows[1][0]), 0)
        self.assertAlmostEqual(float(rows[1][1]), json_thr[0], 6)
        self.assertEqual(int(rows[-1][0]), rq59.N_BOOT - 1)
        self.assertAlmostEqual(float(rows[-1][1]), json_thr[-1], 6)
        # every resample index is contiguous 0..N_BOOT-1.
        idxs = [int(r[0]) for r in rows[1:]]
        self.assertEqual(idxs, list(range(rq59.N_BOOT)))


if __name__ == "__main__":
    unittest.main()
