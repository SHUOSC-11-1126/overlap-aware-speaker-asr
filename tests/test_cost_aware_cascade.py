"""Tests for RQ63: Cost-aware cascade Pareto (experimental/frontier).

Pins the pure helpers: the NEW cost model ``cascade_compute_at_threshold``
(1.0 + 0.428031 * frac, differing from RQ59's 1.93x-base model), the Pareto
efficiency metrics ``pareto_ratio`` / ``marginal_efficiency``, the three
threshold selectors (primary ``select_threshold_by_min_ratio``, secondary
``select_threshold_by_max_ratio`` / ``select_threshold_by_marginal_eff``),
``build_pareto_frontier``, the OOB-eval helper ``cascade_oob_cpwer_and_compute``,
the vectorised ``bootstrap_cost_aware_cascade`` (proved equivalent to the
per-call min-ratio selector), ``jackknife_acceleration``, and ``bca_ci``
(re-exported from RQ59). Also smoke-tests the in-sample cost-aware selection on
the real 77-window AISHELL-4 corpus: RQ43's original-rule cascade @ KL=3.30
reproduces 0.888947, and the central RQ63 finding -- that the cost-aware
(min cpWER/compute) threshold collapses to the SAME aggressive operating point
as RQ54/RQ59 (KL=0.01, 83.1% escalation), killing H63a and H63c -- is pinned.

No Whisper / no audio / no LLM needed. numpy + stdlib only.
"""
from __future__ import annotations

import csv as _csv
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

# The RQ63 analysis script lives in results/frontier/ as a standalone module
# (no src. package), mirroring the RQ54/RQ59 test pattern. The script itself
# adds RQ59 + RQ46 dirs to sys.path and imports them.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_DIR = _PROJECT_ROOT / "results" / "frontier" / "cost_aware_cascade"
sys.path.insert(0, str(_SCRIPT_DIR))

import cost_aware_cascade_analysis as rq63  # noqa: E402  (path-injected import)

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
        self.assertEqual(rq63.N_BOOT, 10000)
        self.assertEqual(rq63.SEED, 42)
        self.assertEqual(rq63.ALPHA, 0.05)

    def test_kl_grid_covers_task_range(self) -> None:
        # Task METHOD: 0.01 .. 8.53 in 0.01 steps = 853 points.
        self.assertEqual(rq63.KL_THRESHOLD_GRID[0], 0.01)
        self.assertEqual(rq63.KL_THRESHOLD_GRID[-1], 8.53)
        self.assertEqual(len(rq63.KL_THRESHOLD_GRID), 853)
        for i in range(1, 10):
            self.assertAlmostEqual(
                rq63.KL_THRESHOLD_GRID[i] - rq63.KL_THRESHOLD_GRID[i - 1], 0.01, 8)

    def test_rq43_anchors_match_task_brief(self) -> None:
        self.assertAlmostEqual(rq63.RQ43_CASCADE_CPWER, 0.888947, 6)
        self.assertAlmostEqual(rq63.RQ43_BASELINE_CPWER, 1.590909, 6)
        self.assertAlmostEqual(rq63.RQ43_BASE_RATIO, 0.428031, 6)
        self.assertEqual(rq63.RQ43_KL_THRESHOLD, 3.30)
        self.assertAlmostEqual(rq63.RQ43_ESCALATION, 0.740260, 6)

    def test_rq54_reference_anchors(self) -> None:
        self.assertEqual(rq63.RQ54_KL_THRESHOLD, 0.01)
        self.assertAlmostEqual(rq63.RQ54_CASCADE_CPWER, 0.777525, 6)
        self.assertAlmostEqual(rq63.RQ54_ESCALATION, 0.831169, 6)
        self.assertAlmostEqual(rq63.RQ54_OOB_MEDIAN_CPWER, 0.779853, 6)

    def test_compute_model_constants(self) -> None:
        # Task METHOD cost model: tiny 1.0x, base adds 0.428031x.
        self.assertEqual(rq63.COMPUTE_TINY, 1.0)
        self.assertAlmostEqual(rq63.COMPUTE_BASE_ADD, 0.428031, 6)
        self.assertAlmostEqual(rq63.COMPUTE_BASE, 1.428031, 6)
        self.assertEqual(rq63.BASELINE_COMPUTE, rq63.COMPUTE_TINY)
        self.assertAlmostEqual(rq63.BASELINE_CPWER, 1.590909, 6)

    def test_hypothesis_kill_thresholds(self) -> None:
        self.assertEqual(rq63.H63A_MAX_ESCALATION, 0.831)
        self.assertEqual(rq63.H63B_MAX_CPWER, 0.889)

    def test_eps_inherited_from_rq59(self) -> None:
        self.assertEqual(rq63.EPS, 1e-9)


# --------------------------------------------------------------- inverse normal CDF (re-exported from RQ59)
class TestNormPpf(unittest.TestCase):
    def test_median_is_zero(self) -> None:
        self.assertAlmostEqual(rq63.norm_ppf(0.5), 0.0, 6)

    def test_known_quantiles(self) -> None:
        self.assertAlmostEqual(rq63.norm_ppf(0.975), 1.959964, 5)
        self.assertAlmostEqual(rq63.norm_ppf(0.025), -1.959964, 5)

    def test_symmetry(self) -> None:
        for p in (0.1, 0.25, 0.4, 0.6, 0.75, 0.9):
            self.assertAlmostEqual(rq63.norm_ppf(p), -rq63.norm_ppf(1.0 - p), 6)

    def test_monotonic_increasing(self) -> None:
        ps = [0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99]
        xs = [rq63.norm_ppf(p) for p in ps]
        for a, b in zip(xs, xs[1:]):
            self.assertLess(a, b)

    def test_endpoints_infinite(self) -> None:
        self.assertEqual(rq63.norm_ppf(0.0), float("-inf"))
        self.assertEqual(rq63.norm_ppf(1.0), float("inf"))


# --------------------------------------------------------------- normal CDF (re-exported from RQ59)
class TestNormCdf(unittest.TestCase):
    def test_roundtrip_with_erf(self) -> None:
        for x in (-2.0, -0.5, 0.0, 0.5, 2.0):
            expected = 0.5 * math.erfc(-x / math.sqrt(2.0))
            self.assertAlmostEqual(rq63.norm_cdf(x), expected, 9)

    def test_known_values(self) -> None:
        self.assertAlmostEqual(rq63.norm_cdf(0.0), 0.5, 9)
        self.assertAlmostEqual(rq63.norm_cdf(1.0), 0.8413447, 6)
        self.assertAlmostEqual(rq63.norm_cdf(-1.0), 0.1586553, 6)


# --------------------------------------------------------------- cascade compute (NEW cost model)
class TestCascadeCompute(unittest.TestCase):
    def test_formula_1_plus_0p428031_frac(self) -> None:
        # 2 of 4 escalated -> frac=0.5 -> compute = 1.0 + 0.428031*0.5
        kl = np.array([0.0, 1.0, 2.0, 3.0])
        comp = rq63.cascade_compute_at_threshold(kl, 1.5)
        self.assertAlmostEqual(comp, 1.0 + 0.428031 * 0.5, 6)

    def test_no_escalation_is_tiny(self) -> None:
        kl = np.array([0.0, 0.1, 0.2])
        self.assertAlmostEqual(rq63.cascade_compute_at_threshold(kl, 10.0), 1.0, 6)

    def test_all_escalation_is_base(self) -> None:
        kl = np.array([5.0, 6.0, 7.0])
        # frac=1.0 -> compute = 1.0 + 0.428031 = 1.428031
        self.assertAlmostEqual(
            rq63.cascade_compute_at_threshold(kl, 0.0), rq63.COMPUTE_BASE, 6)

    def test_partial_escalation(self) -> None:
        kl = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        # threshold 2.5 -> escalate kl>=2.5 (windows 3,4: kl=3.0,4.0) -> frac=2/5=0.4
        comp = rq63.cascade_compute_at_threshold(kl, 2.5)
        self.assertAlmostEqual(comp, 1.0 + 0.428031 * 0.4, 6)

    def test_empty_returns_zero(self) -> None:
        self.assertEqual(rq63.cascade_compute_at_threshold(np.array([]), 1.0), 0.0)

    def test_reproduces_rq43_compute_at_kl_3_30(self) -> None:
        # RQ43 @ KL=3.30: 57/77 escalated -> compute = 1.0 + 0.428031*57/77
        w = rq63.load_rq43_per_window()
        comp = rq63.cascade_compute_at_threshold(w["kl"], 3.30)
        expected = 1.0 + 0.428031 * (57.0 / 77.0)
        self.assertAlmostEqual(comp, expected, 4)


# --------------------------------------------------------------- Pareto ratio
class TestParetoRatio(unittest.TestCase):
    def test_basic_ratio(self) -> None:
        self.assertAlmostEqual(rq63.pareto_ratio(0.8, 1.4), 0.8 / 1.4, 9)

    def test_degenerate_zero_compute(self) -> None:
        self.assertEqual(rq63.pareto_ratio(0.5, 0.0), float("inf"))

    def test_negative_compute(self) -> None:
        self.assertEqual(rq63.pareto_ratio(0.5, -1.0), float("inf"))

    def test_tiny_over_base(self) -> None:
        # tiny-only (no escalation): cpwer=baseline, compute=1.0 -> ratio=baseline
        r = rq63.pareto_ratio(rq63.BASELINE_CPWER, 1.0)
        self.assertAlmostEqual(r, rq63.BASELINE_CPWER, 9)


# --------------------------------------------------------------- marginal efficiency
class TestMarginalEfficiency(unittest.TestCase):
    def test_basic_efficiency(self) -> None:
        # (1.0 - 0.5) / (1.2 - 1.0) = 0.5 / 0.2 = 2.5
        e = rq63.marginal_efficiency(0.5, 1.2, baseline_cpwer=1.0, baseline_compute=1.0)
        self.assertAlmostEqual(e, 2.5, 6)

    def test_no_escalation_returns_neg_inf(self) -> None:
        # compute == baseline_compute -> denom 0 -> -inf
        e = rq63.marginal_efficiency(0.5, 1.0)
        self.assertEqual(e, float("-inf"))

    def test_baseline_point_returns_neg_inf(self) -> None:
        # cpwer == baseline, compute == baseline -> -inf (no marginal compute)
        e = rq63.marginal_efficiency(rq63.BASELINE_CPWER, rq63.BASELINE_COMPUTE)
        self.assertEqual(e, float("-inf"))

    def test_rq54_point_value(self) -> None:
        # At RQ54's point: (1.590909 - 0.777525) / (1.355766 - 1.0) = 2.286289
        e = rq63.marginal_efficiency(0.777525, 1.355766)
        self.assertAlmostEqual(e, 2.286289, 4)


# --------------------------------------------------------------- Pareto dominance (re-exported from RQ46)
class TestParetoDominance(unittest.TestCase):
    def test_strict_dominance(self) -> None:
        # A: cpwer 0.5, compute 1.0 dominates B: cpwer 0.8, compute 1.5
        self.assertTrue(rq63.pareto_dominates(0.5, 1.0, 0.8, 1.5))

    def test_equal_not_dominant(self) -> None:
        # Same point -> not strictly dominant
        self.assertFalse(rq63.pareto_dominates(0.5, 1.0, 0.5, 1.0))

    def test_better_one_axis_worse_other_not_dominant(self) -> None:
        # A better on cpwer but worse on compute -> not dominant
        self.assertFalse(rq63.pareto_dominates(0.4, 1.5, 0.5, 1.0))

    def test_better_both_strict_dominant(self) -> None:
        self.assertTrue(rq63.pareto_dominates(0.3, 0.9, 0.5, 1.0))

    def test_eps_tolerance(self) -> None:
        # Equal on one axis (within eps), strictly better on the other -> dominant
        self.assertTrue(rq63.pareto_dominates(
            0.5, 0.9, 0.5, 1.0, eps=1e-9))
        # Within eps on BOTH axes (no strict win) -> NOT dominant
        self.assertFalse(rq63.pareto_dominates(
            0.5, 1.0 + 1e-12, 0.5, 1.0, eps=1e-9))


# --------------------------------------------------------------- cascade simulation (re-exported from RQ59)
class TestCascadeSimulation(unittest.TestCase):
    def test_no_escalation_equals_tiny_mean(self) -> None:
        tiny = np.array([1.0, 2.0, 3.0, 4.0])
        base = np.array([0.5, 1.0, 1.5, 2.0])
        kl = np.array([0.0, 0.1, 0.2, 0.3])
        cp = rq63.cascade_cpwer_at_threshold(tiny, base, kl, 10.0)
        self.assertAlmostEqual(cp, tiny.mean(), 6)

    def test_all_escalation_equals_base_mean(self) -> None:
        tiny = np.array([1.0, 2.0, 3.0, 4.0])
        base = np.array([0.5, 1.0, 1.5, 2.0])
        kl = np.array([5.0, 6.0, 7.0, 8.0])
        cp = rq63.cascade_cpwer_at_threshold(tiny, base, kl, 0.0)
        self.assertAlmostEqual(cp, base.mean(), 6)

    def test_partial_escalation_mixed_mean(self) -> None:
        tiny = np.array([1.0, 2.0, 3.0, 4.0])
        base = np.array([0.5, 1.0, 1.5, 2.0])
        kl = np.array([0.0, 1.0, 2.0, 3.0])
        # threshold 1.5 -> escalate kl>=1.5 (windows 2,3)
        cp = rq63.cascade_cpwer_at_threshold(tiny, base, kl, 1.5)
        self.assertAlmostEqual(cp, np.mean([1.0, 2.0, 1.5, 2.0]), 6)

    def test_empty_returns_zero(self) -> None:
        cp = rq63.cascade_cpwer_at_threshold(
            np.array([]), np.array([]), np.array([]), 1.0)
        self.assertEqual(cp, 0.0)

    def test_reproduces_rq43_at_kl_3_30(self) -> None:
        w = rq63.load_rq43_per_window()
        cp = rq63.cascade_cpwer_at_threshold(w["tiny"], w["base"], w["kl"], 3.30)
        self.assertAlmostEqual(cp, rq63.RQ43_CASCADE_CPWER, 4)


# --------------------------------------------------------------- select_threshold_by_min_ratio (PRIMARY)
class TestSelectThresholdByMinRatio(unittest.TestCase):
    def test_returns_threshold_from_grid(self) -> None:
        tiny = np.array([2.0, 2.0, 0.1, 0.1])
        base = np.array([0.5, 0.5, 0.5, 0.5])
        kl = np.array([0.0, 1.0, 2.0, 3.0])
        grid = [0.5, 1.5, 2.5]
        out = rq63.select_threshold_by_min_ratio(tiny, base, kl, grid=grid)
        self.assertIn(out["threshold"], grid)

    def test_ratio_is_minimum_over_grid(self) -> None:
        tiny = np.array([2.0, 2.0, 0.1, 0.1])
        base = np.array([0.5, 0.5, 0.5, 0.5])
        kl = np.array([0.0, 1.0, 2.0, 3.0])
        grid = [0.5, 1.5, 2.5]
        out = rq63.select_threshold_by_min_ratio(tiny, base, kl, grid=grid)
        for t in grid:
            cp = rq63.cascade_cpwer_at_threshold(tiny, base, kl, t)
            comp = rq63.cascade_compute_at_threshold(kl, t)
            r = rq63.pareto_ratio(cp, comp)
            self.assertGreaterEqual(r, out["ratio"] - rq63.EPS)

    def test_real_data_collapses_to_rq54_point(self) -> None:
        # CENTRAL RQ63 FINDING: min cpWER/compute collapses to KL=0.01 (RQ54's
        # point), because escalating the 64 highest-KL windows gives the lowest
        # cpWER per compute unit.
        w = rq63.load_rq43_per_window()
        out = rq63.select_threshold_by_min_ratio(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID)
        self.assertAlmostEqual(out["threshold"], 0.01, 6)
        self.assertAlmostEqual(out["cpwer"], rq63.RQ54_CASCADE_CPWER, 4)
        self.assertAlmostEqual(out["frac"], rq63.RQ54_ESCALATION, 4)

    def test_real_data_ratio_below_rq43(self) -> None:
        w = rq63.load_rq43_per_window()
        ca = rq63.select_threshold_by_min_ratio(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID)
        rq43_cp = rq63.cascade_cpwer_at_threshold(
            w["tiny"], w["base"], w["kl"], rq63.RQ43_KL_THRESHOLD)
        rq43_comp = rq63.cascade_compute_at_threshold(w["kl"], rq63.RQ43_KL_THRESHOLD)
        rq43_ratio = rq63.pareto_ratio(rq43_cp, rq43_comp)
        self.assertLess(ca["ratio"], rq43_ratio)

    def test_real_data_ratio_equals_rq54(self) -> None:
        # The cost-aware point IS RQ54's point, so the ratios are equal (not
        # strictly less -- this is why H63c is killed).
        w = rq63.load_rq43_per_window()
        ca = rq63.select_threshold_by_min_ratio(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID)
        rq54_cp = rq63.cascade_cpwer_at_threshold(
            w["tiny"], w["base"], w["kl"], rq63.RQ54_KL_THRESHOLD)
        rq54_comp = rq63.cascade_compute_at_threshold(w["kl"], rq63.RQ54_KL_THRESHOLD)
        rq54_ratio = rq63.pareto_ratio(rq54_cp, rq54_comp)
        self.assertAlmostEqual(ca["ratio"], rq54_ratio, 4)


# --------------------------------------------------------------- select_threshold_by_max_ratio (SECONDARY)
class TestSelectThresholdByMaxRatio(unittest.TestCase):
    def test_real_data_collapses_to_all_tiny(self) -> None:
        # Maximising cpWER/compute collapses to the all-tiny corner (no
        # escalation, compute 1.0x) -- degenerate, fails H63b trivially.
        w = rq63.load_rq43_per_window()
        out = rq63.select_threshold_by_max_ratio(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID)
        self.assertAlmostEqual(out["threshold"], 8.53, 6)
        self.assertAlmostEqual(out["frac"], 0.0, 6)
        self.assertAlmostEqual(out["compute"], 1.0, 6)
        self.assertAlmostEqual(out["cpwer"], rq63.BASELINE_CPWER, 4)

    def test_ratio_is_maximum_over_grid(self) -> None:
        tiny = np.array([2.0, 2.0, 0.1, 0.1])
        base = np.array([0.5, 0.5, 0.5, 0.5])
        kl = np.array([0.0, 1.0, 2.0, 3.0])
        grid = [0.5, 1.5, 2.5]
        out = rq63.select_threshold_by_max_ratio(tiny, base, kl, grid=grid)
        for t in grid:
            cp = rq63.cascade_cpwer_at_threshold(tiny, base, kl, t)
            comp = rq63.cascade_compute_at_threshold(kl, t)
            r = rq63.pareto_ratio(cp, comp)
            self.assertLessEqual(r, out["ratio"] + rq63.EPS)

    def test_returns_threshold_from_grid(self) -> None:
        tiny = np.array([2.0, 2.0, 0.1, 0.1])
        base = np.array([0.5, 0.5, 0.5, 0.5])
        kl = np.array([0.0, 1.0, 2.0, 3.0])
        grid = [0.5, 1.5, 2.5]
        out = rq63.select_threshold_by_max_ratio(tiny, base, kl, grid=grid)
        self.assertIn(out["threshold"], grid)


# --------------------------------------------------------------- select_threshold_by_marginal_eff (SECONDARY)
class TestSelectThresholdByMarginalEff(unittest.TestCase):
    def test_real_data_collapses_to_rq54_point(self) -> None:
        # Marginal efficiency (bang-for-buck) also collapses to KL=0.01 on the
        # real data: escalating the 64 highest-KL windows gives the most cpWER
        # reduction per compute unit.
        w = rq63.load_rq43_per_window()
        out = rq63.select_threshold_by_marginal_eff(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID)
        self.assertAlmostEqual(out["threshold"], 0.01, 6)
        self.assertAlmostEqual(out["cpwer"], rq63.RQ54_CASCADE_CPWER, 4)

    def test_marginal_efficiency_value(self) -> None:
        w = rq63.load_rq43_per_window()
        out = rq63.select_threshold_by_marginal_eff(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID)
        self.assertAlmostEqual(out["marginal_efficiency"], 2.286289, 3)

    def test_efficiency_is_maximum_over_grid(self) -> None:
        w = rq63.load_rq43_per_window()
        ca = rq63.select_threshold_by_marginal_eff(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID)
        for t in rq63.KL_THRESHOLD_GRID[:20]:  # spot-check first 20
            cp = rq63.cascade_cpwer_at_threshold(w["tiny"], w["base"], w["kl"], t)
            comp = rq63.cascade_compute_at_threshold(w["kl"], t)
            e = rq63.marginal_efficiency(cp, comp)
            if e > float("-inf"):
                self.assertLessEqual(e, ca["marginal_efficiency"] + rq63.EPS)


# --------------------------------------------------------------- build_pareto_frontier
class TestBuildParetoFrontier(unittest.TestCase):
    def test_length_matches_grid(self) -> None:
        w = rq63.load_rq43_per_window()
        frontier = rq63.build_pareto_frontier(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID)
        self.assertEqual(len(frontier), len(rq63.KL_THRESHOLD_GRID))

    def test_keys_present(self) -> None:
        w = rq63.load_rq43_per_window()
        frontier = rq63.build_pareto_frontier(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID)
        for pt in frontier:
            for key in ("threshold", "cpwer", "compute", "frac",
                        "cpwer_per_compute", "marginal_efficiency"):
                self.assertIn(key, pt)

    def test_rq43_point_present(self) -> None:
        w = rq63.load_rq43_per_window()
        frontier = rq63.build_pareto_frontier(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID)
        # KL=3.30 is in the grid (0.01 step). Find it.
        pt = next(p for p in frontier if abs(p["threshold"] - 3.30) < 1e-9)
        self.assertAlmostEqual(pt["cpwer"], rq63.RQ43_CASCADE_CPWER, 4)

    def test_all_tiny_corner(self) -> None:
        w = rq63.load_rq43_per_window()
        frontier = rq63.build_pareto_frontier(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID)
        pt = next(p for p in frontier if abs(p["threshold"] - 8.53) < 1e-9)
        self.assertAlmostEqual(pt["frac"], 0.0, 6)
        self.assertAlmostEqual(pt["compute"], 1.0, 6)
        self.assertAlmostEqual(pt["cpwer"], rq63.BASELINE_CPWER, 4)


# --------------------------------------------------------------- cascade_oob_cpwer_and_compute
class TestCascadeOobCpwerAndCompute(unittest.TestCase):
    def test_empty_oob_returns_nan(self) -> None:
        tiny = np.array([1.0, 2.0, 3.0])
        base = np.array([0.5, 1.0, 1.5])
        kl = np.array([0.0, 1.0, 2.0])
        # in_bag covers all windows -> OOB empty
        out = rq63.cascade_oob_cpwer_and_compute(
            tiny, base, kl, 1.0, np.array([0, 1, 2]))
        self.assertTrue(math.isnan(out["cpwer"]))
        self.assertTrue(math.isnan(out["compute"]))
        self.assertEqual(out["n_oob"], 0)

    def test_matches_manual_computation(self) -> None:
        tiny = np.array([1.0, 2.0, 3.0, 4.0])
        base = np.array([0.5, 1.0, 1.5, 2.0])
        kl = np.array([0.0, 1.0, 2.0, 3.0])
        # in_bag = [0, 0] -> OOB = {1, 2, 3}
        out = rq63.cascade_oob_cpwer_and_compute(
            tiny, base, kl, 1.5, np.array([0, 0]))
        self.assertEqual(out["n_oob"], 3)
        # OOB windows: kl=[1.0, 2.0, 3.0], threshold 1.5 -> escalate kl>=1.5 (2.0, 3.0)
        # selected = [tiny1, base2, base3] = [2.0, 1.5, 2.0] -> mean = 1.8333
        self.assertAlmostEqual(out["cpwer"], np.mean([2.0, 1.5, 2.0]), 6)
        # frac = 2/3 escalated
        expected_compute = 1.0 + 0.428031 * (2.0 / 3.0)
        self.assertAlmostEqual(out["compute"], expected_compute, 6)
        self.assertEqual(out["n_escalated"], 2)

    def test_oob_compute_formula(self) -> None:
        tiny = np.array([1.0, 2.0, 3.0, 4.0])
        base = np.array([0.5, 1.0, 1.5, 2.0])
        kl = np.array([0.0, 1.0, 2.0, 3.0])
        out = rq63.cascade_oob_cpwer_and_compute(
            tiny, base, kl, 0.0, np.array([0]))  # OOB = {1,2,3}, all escalated
        self.assertAlmostEqual(out["compute"], rq63.COMPUTE_BASE, 6)

    def test_all_in_bag_no_oob(self) -> None:
        tiny = np.array([1.0, 2.0])
        base = np.array([0.5, 1.0])
        kl = np.array([0.0, 1.0])
        out = rq63.cascade_oob_cpwer_and_compute(
            tiny, base, kl, 0.5, np.array([0, 1, 0, 1]))
        self.assertEqual(out["n_oob"], 0)


# --------------------------------------------------------------- bootstrap_cost_aware_cascade
class TestBootstrapCostAwareCascade(unittest.TestCase):
    def test_determinism_same_seed(self) -> None:
        w = rq63.load_rq43_per_window()
        out1 = rq63.bootstrap_cost_aware_cascade(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID,
            n_boot=10, seed=42)
        out2 = rq63.bootstrap_cost_aware_cascade(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID,
            n_boot=10, seed=42)
        np.testing.assert_array_equal(out1["boot_idx"], out2["boot_idx"])
        np.testing.assert_array_equal(out1["thresholds"], out2["thresholds"])

    def test_thresholds_shape(self) -> None:
        w = rq63.load_rq43_per_window()
        out = rq63.bootstrap_cost_aware_cascade(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID,
            n_boot=20, seed=42)
        self.assertEqual(out["thresholds"].shape, (20,))
        self.assertEqual(out["oob_cpwer"].shape, (20,))
        self.assertEqual(out["boot_idx"].shape, (20, 77))

    def test_oob_sizes_reasonable(self) -> None:
        # Expected OOB size ~ n * (1 - 1/n)^n ~ 77 * e^-1 ~ 28.3
        w = rq63.load_rq43_per_window()
        out = rq63.bootstrap_cost_aware_cascade(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID,
            n_boot=50, seed=42)
        mean_oob = float(np.mean(out["n_oob"]))
        self.assertGreater(mean_oob, 15.0)
        self.assertLess(mean_oob, 45.0)

    def test_vectorised_matches_select_min_ratio(self) -> None:
        # The vectorised bootstrap's in-bag threshold selection must match the
        # per-call select_threshold_by_min_ratio on each resample's in-bag windows.
        w = rq63.load_rq43_per_window()
        tiny, base, kl = w["tiny"], w["base"], w["kl"]
        out = rq63.bootstrap_cost_aware_cascade(
            tiny, base, kl, grid=rq63.KL_THRESHOLD_GRID, n_boot=15, seed=42)
        for b in range(15):
            idx = out["boot_idx"][b]
            expected = rq63.select_threshold_by_min_ratio(
                tiny[idx], base[idx], kl[idx], grid=rq63.KL_THRESHOLD_GRID)
            self.assertAlmostEqual(
                float(out["thresholds"][b]), expected["threshold"], 6,
                msg=f"resample {b}: vectorised {out['thresholds'][b]} != "
                    f"per-call {expected['threshold']}")

    def test_small_bootstrap_valid_output(self) -> None:
        w = rq63.load_rq43_per_window()
        out = rq63.bootstrap_cost_aware_cascade(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID,
            n_boot=30, seed=42)
        valid = out["oob_cpwer"][~np.isnan(out["oob_cpwer"])]
        self.assertGreater(len(valid), 0)
        # OOB cpWER is a mean of per-window cpWERs in [0, ~2.4].
        self.assertTrue(np.all(valid >= 0.0))
        self.assertTrue(np.all(valid < 3.0))
        # All thresholds must be in the grid.
        for t in out["thresholds"]:
            self.assertIn(float(t), rq63.KL_THRESHOLD_GRID)


# --------------------------------------------------------------- jackknife acceleration
class TestJackknife(unittest.TestCase):
    def test_theta_loo_length(self) -> None:
        w = rq63.load_rq43_per_window()
        a, theta_loo = rq63.jackknife_acceleration(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID)
        self.assertEqual(theta_loo.shape, (77,))

    def test_theta_loo_finite(self) -> None:
        w = rq63.load_rq43_per_window()
        a, theta_loo = rq63.jackknife_acceleration(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID)
        self.assertTrue(np.all(np.isfinite(theta_loo)))
        self.assertTrue(math.isfinite(a))

    def test_acceleration_formula(self) -> None:
        # Synthetic: constant theta_loo -> a = 0.
        tiny = np.array([1.0, 1.0, 1.0, 1.0])
        base = np.array([0.5, 0.5, 0.5, 0.5])
        kl = np.array([0.0, 0.0, 0.0, 0.0])
        grid = [0.5, 1.0]
        a, theta_loo = rq63.jackknife_acceleration(tiny, base, kl, grid=grid)
        # All LOO samples are identical -> diff = 0 -> a = 0.
        self.assertAlmostEqual(a, 0.0, 9)

    def test_matches_per_call_select(self) -> None:
        # theta_loo[i] = cascade_cpwer_at_threshold on (n-1 windows) at the
        # LOO min-ratio threshold.
        w = rq63.load_rq43_per_window()
        tiny, base, kl = w["tiny"], w["base"], w["kl"]
        a, theta_loo = rq63.jackknife_acceleration(
            tiny, base, kl, grid=rq63.KL_THRESHOLD_GRID)
        i = 0
        mask = np.ones(77, dtype=bool)
        mask[i] = False
        sel = rq63.select_threshold_by_min_ratio(
            tiny[mask], base[mask], kl[mask], grid=rq63.KL_THRESHOLD_GRID)
        expected = rq63.cascade_cpwer_at_threshold(
            tiny[mask], base[mask], kl[mask], sel["threshold"])
        self.assertAlmostEqual(float(theta_loo[i]), expected, 6)


# --------------------------------------------------------------- BCa CI (re-exported from RQ59)
class TestBCa(unittest.TestCase):
    def test_basic_ci(self) -> None:
        rng = np.random.default_rng(0)
        boot = rng.normal(0.5, 0.1, size=1000)
        bca = rq63.bca_ci(0.5, boot, accel=0.0, alpha=0.05)
        self.assertLess(bca["lo"], bca["hi"])
        self.assertIn(bca["method"], ("bca", "percentile_fallback"))
        self.assertLessEqual(bca["lo"], bca["median"] + 1e-6)
        self.assertGreaterEqual(bca["hi"], bca["median"] - 1e-6)

    def test_empty_returns_nan(self) -> None:
        bca = rq63.bca_ci(0.5, np.array([]), accel=0.0, alpha=0.05)
        self.assertTrue(math.isnan(bca["lo"]))
        self.assertTrue(math.isnan(bca["hi"]))
        self.assertEqual(bca["method"], "empty")

    def test_brackets_median(self) -> None:
        boot = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
        bca = rq63.bca_ci(0.5, boot, accel=0.0, alpha=0.05)
        self.assertLessEqual(bca["lo"], bca["median"] + 1e-9)
        self.assertGreaterEqual(bca["hi"], bca["median"] - 1e-9)


# --------------------------------------------------------------- write_bootstrap_csv
class TestWriteBootstrapCsv(unittest.TestCase):
    def test_header_and_rows(self) -> None:
        tmp = _SCRIPT_DIR / "_test_csv_tmp.csv"
        try:
            boot_idx = np.array([[0, 1, 2, 0], [0, 1, 0, 1], [0, 1, 2, 3]])
            thr = np.array([0.5, 1.0, 2.0])
            oob_cp = np.array([0.4, float("nan"), 0.7])
            oob_co = np.array([1.2, float("nan"), 1.3])
            n_oob = np.array([2, 0, 4])
            n_esc = np.array([1, 0, 2])
            rq63.write_bootstrap_csv(tmp, boot_idx, thr, oob_cp, oob_co,
                                     n_oob, n_esc, 4)
            with tmp.open() as fh:
                rows = list(_csv.reader(fh))
            self.assertEqual(rows[0], [
                "resample", "threshold", "oob_cpwer", "oob_compute",
                "n_oob", "n_escalated_oob", "oob_fraction",
                "escalation_fraction_oob"])
            self.assertEqual(len(rows), 4)  # header + 3
            self.assertEqual(rows[1][0], "0")
            self.assertEqual(rows[1][1], "0.5")
            self.assertEqual(rows[1][2], "0.4")
            self.assertEqual(rows[1][3], "1.2")
            # row 2 has empty OOB -> blank cpwer, blank compute
            self.assertEqual(rows[2][2], "")
            self.assertEqual(rows[2][3], "")
            self.assertEqual(rows[2][4], "0")
        finally:
            if tmp.exists():
                tmp.unlink()

    def test_nan_handling(self) -> None:
        tmp = _SCRIPT_DIR / "_test_csv_tmp2.csv"
        try:
            boot_idx = np.array([[0, 1], [0, 1]])
            thr = np.array([0.5, 1.0])
            oob_cp = np.array([float("nan"), 0.3])
            oob_co = np.array([float("nan"), 1.1])
            n_oob = np.array([0, 2])
            n_esc = np.array([0, 1])
            rq63.write_bootstrap_csv(tmp, boot_idx, thr, oob_cp, oob_co,
                                     n_oob, n_esc, 2)
            with tmp.open() as fh:
                rows = list(_csv.reader(fh))
            # First data row has nan -> blank
            self.assertEqual(rows[1][2], "")
            self.assertEqual(rows[1][3], "")
            self.assertEqual(rows[1][6], "0.0")  # oob_fraction = 0/2 = 0
            self.assertEqual(rows[1][7], "")    # esc frac blank (n_oob=0)
        finally:
            if tmp.exists():
                tmp.unlink()


# --------------------------------------------------------------- end-to-end smoke
class TestEndToEnd(unittest.TestCase):
    def test_load_rq43_per_window(self) -> None:
        w = rq63.load_rq43_per_window()
        self.assertEqual(len(w["tiny"]), 77)
        self.assertEqual(len(w["base"]), 77)
        self.assertEqual(len(w["kl"]), 77)
        self.assertAlmostEqual(float(w["tiny"].mean()), rq63.RQ43_BASELINE_CPWER, 4)

    def test_label_counts_37_40(self) -> None:
        w = rq63.load_rq43_per_window()
        labels = (w["tiny"] > rq63.CATASTROPHIC_CPWER).astype(int)
        self.assertEqual(int(labels.sum()), 37)
        self.assertEqual(int((labels == 0).sum()), 40)

    def test_rq43_reproduction_under_new_cost_model(self) -> None:
        # The cpWER anchor reproduces (cost model only changes compute axis).
        w = rq63.load_rq43_per_window()
        cp = rq63.cascade_cpwer_at_threshold(w["tiny"], w["base"], w["kl"], 3.30)
        self.assertAlmostEqual(cp, rq63.RQ43_CASCADE_CPWER, 4)
        comp = rq63.cascade_compute_at_threshold(w["kl"], 3.30)
        # Under RQ63 cost model: 1.0 + 0.428031 * 57/77
        self.assertAlmostEqual(comp, 1.0 + 0.428031 * (57.0 / 77.0), 4)

    def test_small_bootstrap_end_to_end(self) -> None:
        w = rq63.load_rq43_per_window()
        out = rq63.bootstrap_cost_aware_cascade(
            w["tiny"], w["base"], w["kl"], grid=rq63.KL_THRESHOLD_GRID,
            n_boot=30, seed=42)
        self.assertEqual(out["thresholds"].shape, (30,))
        valid = out["oob_cpwer"][~np.isnan(out["oob_cpwer"])]
        self.assertGreater(len(valid), 0)
        self.assertTrue(np.all(valid >= 0.0))
        self.assertTrue(np.all(valid < 3.0))

    def test_results_json_written_and_consistent(self) -> None:
        # The generated results JSON must exist, be labelled experimental/
        # frontier, and report the three hypothesis verdicts consistently.
        out_json = rq63.OUT_JSON
        self.assertTrue(out_json.exists(), f"missing {out_json}")
        data = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertEqual(data["label"], "experimental/frontier")
        self.assertEqual(data["n_windows"], 77)
        self.assertEqual(data["n_hallucinated"], 37)
        self.assertEqual(data["n_clean"], 40)
        # H63a: escalation fraction >= 0.831 -> KILLED (collapses to RQ54 point).
        frac = data["in_sample_cost_aware_point_primary"]["escalation_fraction"]
        self.assertGreaterEqual(frac, rq63.H63A_MAX_ESCALATION - 1e-6)
        self.assertEqual(data["hypothesis_verdicts"]["H63a"]["supported"], False)
        # H63b: OOB median cpWER <= 0.889 -> SUPPORTED.
        med = data["bootstrap_oob_cpwer_distribution"]["median"]
        self.assertLessEqual(med, rq63.H63B_MAX_CPWER)
        self.assertEqual(data["hypothesis_verdicts"]["H63b"]["supported"], True)
        # H63c: ratio equals RQ54 (not strictly lower) -> KILLED.
        self.assertEqual(data["hypothesis_verdicts"]["H63c"]["supported"], False)
        # BCa CI must bracket the OOB median.
        self.assertLessEqual(data["bca_ci"]["lo"], med + 1e-6)
        self.assertGreaterEqual(data["bca_ci"]["hi"], med - 1e-6)
        # Bootstrap arrays must have length N_BOOT.
        self.assertEqual(len(data["per_bootstrap"]["thresholds"]), rq63.N_BOOT)
        self.assertEqual(len(data["per_bootstrap"]["oob_cpwer"]), rq63.N_BOOT)

    def test_results_json_cost_aware_equals_rq54_point(self) -> None:
        # The headline RQ63 finding: the cost-aware (min-ratio) point IS RQ54's
        # operating point (KL=0.01, 83.1% escalation, cpWER 0.777525).
        data = json.loads(rq63.OUT_JSON.read_text(encoding="utf-8"))
        ca = data["in_sample_cost_aware_point_primary"]
        self.assertAlmostEqual(ca["threshold"], rq63.RQ54_KL_THRESHOLD, 6)
        self.assertAlmostEqual(ca["cascade_cpwer"], rq63.RQ54_CASCADE_CPWER, 4)
        self.assertAlmostEqual(ca["escalation_fraction"], rq63.RQ54_ESCALATION, 4)

    def test_results_json_secondary_max_ratio_is_all_tiny(self) -> None:
        data = json.loads(rq63.OUT_JSON.read_text(encoding="utf-8"))
        ca_max = data["in_sample_cost_aware_point_secondary_max_ratio"]
        self.assertAlmostEqual(ca_max["threshold"], 8.53, 6)
        self.assertAlmostEqual(ca_max["escalation_fraction"], 0.0, 6)
        self.assertAlmostEqual(ca_max["cascade_compute"], 1.0, 6)


# --------------------------------------------------------------- CSV output
class TestCSVOutput(unittest.TestCase):
    def test_results_csv_columns(self) -> None:
        out_csv = rq63.OUT_CSV
        self.assertTrue(out_csv.exists(), f"missing {out_csv}")
        with out_csv.open() as fh:
            reader = _csv.reader(fh)
            header = next(reader)
        self.assertEqual(header[:4], ["resample", "threshold", "oob_cpwer",
                                      "oob_compute"])
        self.assertIn("n_oob", header)
        self.assertIn("n_escalated_oob", header)

    def test_results_csv_row_count(self) -> None:
        out_csv = rq63.OUT_CSV
        with out_csv.open() as fh:
            rows = list(_csv.reader(fh))
        # N_BOOT data rows + 1 header.
        self.assertEqual(len(rows), rq63.N_BOOT + 1)
        # Every resample index is contiguous 0..N_BOOT-1.
        idxs = [int(r[0]) for r in rows[1:]]
        self.assertEqual(idxs, list(range(rq63.N_BOOT)))

    def test_results_csv_consistent_with_json(self) -> None:
        out_csv = rq63.OUT_CSV
        data = json.loads(rq63.OUT_JSON.read_text(encoding="utf-8"))
        json_thr = data["per_bootstrap"]["thresholds"]
        with out_csv.open() as fh:
            rows = list(_csv.reader(fh))
        # Spot-check first and last resample threshold match JSON.
        self.assertAlmostEqual(float(rows[1][1]), json_thr[0], 6)
        self.assertAlmostEqual(float(rows[-1][1]), json_thr[-1], 6)


if __name__ == "__main__":
    unittest.main()
