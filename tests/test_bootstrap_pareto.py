"""Tests for RQ46: Bootstrap Pareto frontier confidence intervals.

experimental/frontier. Closes #957.

Pins the pure helpers used by
``results/frontier/bootstrap_pareto/bootstrap_pareto_analysis.py``:

  * escalation mask (strict ``>``, matches RQ43) and escalation fraction
  * cascade cpWER aggregation (mean of selected tiny/base per window)
  * cascade compute (``compute_tiny*(1-f) + compute_base*f``)
  * bootstrap resample (seeded, with replacement, in-range)
  * Pareto dominance (strict, both axes, one strict)
  * percentile CI / median
  * in-sample Pareto point / curve
  * vectorised bootstrap Pareto curve: shape + exact consistency with the pure
    helpers on a small case + bootstrap-mean == in-sample mean for the mean
    statistic

Smoke test: the in-sample Pareto curve on the real RQ43 per-window data
reproduces RQ43's reported operating point (cascade @ KL=3.30 cpWER 0.888947,
compute 1.688442x, frac 0.74026) and the always-tiny baseline cpWER 1.590909.

Run: /opt/homebrew/bin/python3 -m unittest tests.test_bootstrap_pareto -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

# The RQ46 analysis script lives in results/frontier/ as a standalone module
# (mirrors RQ43/RQ19 layout). Import via sys.path manipulation.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_DIR = _PROJECT_ROOT / "results" / "frontier" / "bootstrap_pareto"
sys.path.insert(0, str(_SCRIPT_DIR))

import bootstrap_pareto_analysis as bp  # noqa: E402  (path-injected import)


# ------------------------------------------------------------- escalation mask
class TestEscalationMask(unittest.TestCase):
    def test_strict_greater_only(self) -> None:
        # KL == threshold is NOT escalated (strict >, matches RQ43)
        m = bp.escalation_mask([3.30, 3.31, 3.29], 3.30)
        self.assertEqual(m, [False, True, False])

    def test_above_escalated(self) -> None:
        self.assertEqual(bp.escalation_mask([0.0, 5.0, 8.5], 4.0), [False, True, True])

    def test_empty(self) -> None:
        self.assertEqual(bp.escalation_mask([], 3.30), [])

    def test_all_below_threshold(self) -> None:
        self.assertEqual(
            bp.escalation_mask([1.0, 2.0, 3.0], 3.30),
            [False, False, False],
        )


# ------------------------------------------------------ escalation fraction
class TestComputeEscalationFraction(unittest.TestCase):
    def test_all_false_is_zero(self) -> None:
        self.assertEqual(bp.compute_escalation_fraction([False, False, False]), 0.0)

    def test_all_true_is_one(self) -> None:
        self.assertEqual(bp.compute_escalation_fraction([True, True]), 1.0)

    def test_mixed(self) -> None:
        self.assertAlmostEqual(bp.compute_escalation_fraction([True, False, True]), 2 / 3)

    def test_empty_is_zero(self) -> None:
        self.assertEqual(bp.compute_escalation_fraction([]), 0.0)


# --------------------------------------------------------- cascade cpWER
class TestComputeCascadeCpwer(unittest.TestCase):
    def test_no_escalation_equals_tiny_mean(self) -> None:
        tiny = [1.0, 2.0, 3.0]
        base = [0.4, 0.8, 1.2]
        self.assertAlmostEqual(
            bp.compute_cascade_cpwer(tiny, base, [False, False, False]),
            2.0,
        )

    def test_all_escalation_equals_base_mean(self) -> None:
        tiny = [1.0, 2.0, 3.0]
        base = [0.4, 0.8, 1.2]
        self.assertAlmostEqual(
            bp.compute_cascade_cpwer(tiny, base, [True, True, True]),
            (0.4 + 0.8 + 1.2) / 3,
        )

    def test_mixed_selection(self) -> None:
        tiny = [1.0, 2.0, 3.0]
        base = [0.4, 0.8, 1.2]
        # escalate middle only -> (1.0 + 0.8 + 3.0)/3
        self.assertAlmostEqual(
            bp.compute_cascade_cpwer(tiny, base, [False, True, False]),
            (1.0 + 0.8 + 3.0) / 3,
        )

    def test_empty_is_zero(self) -> None:
        self.assertEqual(bp.compute_cascade_cpwer([], [], []), 0.0)

    def test_length_mismatch_raises(self) -> None:
        with self.assertRaises(AssertionError):
            bp.compute_cascade_cpwer([1.0, 2.0], [0.4], [True, False])


# --------------------------------------------------------- cascade compute
class TestComputeCascadeCompute(unittest.TestCase):
    def test_no_escalation_equals_tiny_compute(self) -> None:
        self.assertAlmostEqual(
            bp.compute_cascade_compute([False, False], 1.0, 1.93),
            1.0,
        )

    def test_all_escalation_equals_base_compute(self) -> None:
        self.assertAlmostEqual(
            bp.compute_cascade_compute([True, True], 1.0, 1.93),
            1.93,
        )

    def test_half_escalation(self) -> None:
        # f = 0.5 -> compute = 1.0*0.5 + 1.93*0.5 = 1.465
        self.assertAlmostEqual(
            bp.compute_cascade_compute([True, False], 1.0, 1.93),
            1.465,
        )

    def test_value_at_rq43_primary_frac(self) -> None:
        # RQ43 primary: frac 0.74026 -> compute 1.688442
        mask = [True] * 57 + [False] * 20  # 57/77 = 0.74026
        compute = bp.compute_cascade_compute(mask, 1.0, 1.93)
        self.assertAlmostEqual(compute, 1.688442, places=4)

    def test_empty_is_tiny_compute(self) -> None:
        self.assertAlmostEqual(bp.compute_cascade_compute([], 1.0, 1.93), 1.0)


# --------------------------------------------------------- bootstrap resample
class TestBootstrapResample(unittest.TestCase):
    def test_deterministic_with_seed(self) -> None:
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)
        a = bp.bootstrap_resample(rng1, 77)
        b = bp.bootstrap_resample(rng2, 77)
        np.testing.assert_array_equal(a, b)

    def test_in_range(self) -> None:
        rng = np.random.default_rng(7)
        idx = bp.bootstrap_resample(rng, 77)
        self.assertEqual(idx.shape, (77,))
        self.assertTrue(np.all(idx >= 0))
        self.assertTrue(np.all(idx < 77))

    def test_with_replacement_allows_duplicates(self) -> None:
        # With n=77 draws from [0,77), duplicates are essentially guaranteed;
        # the number of UNIQUE indices is < 77 with overwhelming probability.
        rng = np.random.default_rng(42)
        idx = bp.bootstrap_resample(rng, 77)
        self.assertLess(len(set(idx.tolist())), 77)

    def test_different_seeds_differ(self) -> None:
        a = bp.bootstrap_resample(np.random.default_rng(1), 50)
        b = bp.bootstrap_resample(np.random.default_rng(2), 50)
        self.assertFalse(np.array_equal(a, b))


# --------------------------------------------------------- Pareto dominance
class TestParetoDominates(unittest.TestCase):
    def test_strictly_better_both_dominates(self) -> None:
        self.assertTrue(bp.pareto_dominates(0.5, 1.5, 1.0, 2.0))

    def test_equal_on_both_no_domination(self) -> None:
        self.assertFalse(bp.pareto_dominates(1.0, 1.5, 1.0, 1.5))

    def test_better_cpwer_equal_compute_dominates(self) -> None:
        self.assertTrue(bp.pareto_dominates(0.8, 1.5, 1.0, 1.5))

    def test_better_compute_equal_cpwer_dominates(self) -> None:
        self.assertTrue(bp.pareto_dominates(1.0, 1.4, 1.0, 1.5))

    def test_better_cpwer_worse_compute_no_domination(self) -> None:
        # lower cpWER but higher compute -> trade-off, no dominance
        self.assertFalse(bp.pareto_dominates(0.8, 1.8, 1.0, 1.5))

    def test_symmetric_neither_dominates(self) -> None:
        # A better on cpWER, B better on compute -> trade-off, neither dominates.
        self.assertFalse(bp.pareto_dominates(0.8, 2.0, 1.0, 1.8))
        self.assertFalse(bp.pareto_dominates(1.0, 1.8, 0.8, 2.0))


# --------------------------------------------------------- percentile CI
class TestPercentileCi(unittest.TestCase):
    def test_basic_percentiles(self) -> None:
        vals = list(range(0, 101))  # 0..100
        lo, hi, med = bp.percentile_ci(vals, 2.5, 97.5)
        self.assertAlmostEqual(lo, 2.5)
        self.assertAlmostEqual(hi, 97.5)
        self.assertAlmostEqual(med, 50.0)

    def test_median_of_even_set(self) -> None:
        _, _, med = bp.percentile_ci([1.0, 2.0, 3.0, 4.0])
        self.assertAlmostEqual(med, 2.5)

    def test_empty_returns_nan(self) -> None:
        lo, hi, med = bp.percentile_ci([])
        self.assertTrue(np.isnan(lo))
        self.assertTrue(np.isnan(hi))
        self.assertTrue(np.isnan(med))

    def test_ci_bounds_ordering(self) -> None:
        lo, hi, _ = bp.percentile_ci([5.0, 1.0, 3.0, 2.0, 4.0], 10.0, 90.0)
        self.assertLessEqual(lo, hi)


# --------------------------------------------------------- Pareto point / curve
class TestComputeParetoPoint(unittest.TestCase):
    def test_point_fields(self) -> None:
        tiny = [1.0, 2.0, 3.0, 0.5]
        base = [0.4, 0.8, 1.2, 0.2]
        kl = [0.0, 3.5, 5.0, 1.0]
        pt = bp.compute_pareto_point(tiny, base, kl, 3.0)
        self.assertEqual(pt["threshold"], 3.0)
        self.assertIn("cpwer", pt)
        self.assertIn("compute", pt)
        self.assertIn("frac", pt)
        self.assertIn("mask", pt)

    def test_point_mask_strict(self) -> None:
        kl = [3.0, 3.30, 3.31]
        pt = bp.compute_pareto_point([1, 1, 1], [0, 0, 0], kl, 3.30)
        self.assertEqual(pt["mask"], [False, False, True])

    def test_point_cpwer_matches_manual(self) -> None:
        tiny = [1.0, 2.0, 3.0]
        base = [0.4, 0.8, 1.2]
        kl = [0.0, 5.0, 1.0]  # only middle escalates at thr 3.0
        pt = bp.compute_pareto_point(tiny, base, kl, 3.0)
        self.assertAlmostEqual(pt["cpwer"], (1.0 + 0.8 + 3.0) / 3)
        self.assertAlmostEqual(pt["frac"], 1 / 3)


class TestComputeParetoCurve(unittest.TestCase):
    def test_curve_length_matches_thresholds(self) -> None:
        tiny = [1.0, 2.0, 3.0]
        base = [0.4, 0.8, 1.2]
        kl = [0.0, 3.5, 5.0]
        curve = bp.compute_pareto_curve(tiny, base, kl, [0.0, 3.0, 6.0])
        self.assertEqual(len(curve), 3)
        self.assertEqual([p["threshold"] for p in curve], [0.0, 3.0, 6.0])

    def test_higher_threshold_lower_escalation_fraction(self) -> None:
        # Monotone: as threshold rises, fewer windows escalate.
        tiny = [1.0, 2.0, 3.0, 4.0]
        base = [0.4, 0.8, 1.2, 1.6]
        kl = [1.0, 2.0, 4.0, 6.0]
        fracs = [
            bp.compute_pareto_point(tiny, base, kl, t)["frac"]
            for t in [0.0, 1.5, 3.0, 5.0, 7.0]
        ]
        for a, b in zip(fracs, fracs[1:]):
            self.assertGreaterEqual(a, b)


# --------------------------------------------------------- bootstrap curve
class TestBootstrapParetoCurve(unittest.TestCase):
    def test_shape(self) -> None:
        tiny = [1.0, 2.0, 3.0, 0.5]
        base = [0.4, 0.8, 1.2, 0.2]
        kl = [0.0, 3.5, 5.0, 1.0]
        cpw, cmp_, fr = bp.bootstrap_pareto_curve(
            tiny, base, kl, [0.0, 3.0, 5.0], n_boot=10, seed=42)
        self.assertEqual(cpw.shape, (10, 3))
        self.assertEqual(cmp_.shape, (10, 3))
        self.assertEqual(fr.shape, (10, 3))

    def test_consistency_with_pure_helpers(self) -> None:
        # The vectorised bootstrap must match the pure helpers per-resample,
        # per-threshold when given the SAME index draw.
        tiny = [1.0, 2.0, 3.0, 0.5]
        base = [0.4, 0.8, 1.2, 0.2]
        kl = [0.0, 3.5, 5.0, 1.0]
        thresholds = [0.0, 3.0, 4.0]
        B = 5
        seed = 42
        cpw, cmp_, fr = bp.bootstrap_pareto_curve(
            tiny, base, kl, thresholds, n_boot=B, seed=seed)
        # Replicate the exact draw the vectorised path makes.
        rng = np.random.default_rng(seed)
        idx = rng.integers(0, 4, size=(B, 4))
        for b in range(B):
            tiny_b = [tiny[i] for i in idx[b]]
            base_b = [base[i] for i in idx[b]]
            kl_b = [kl[i] for i in idx[b]]
            for t_i, thr in enumerate(thresholds):
                pt = bp.compute_pareto_point(tiny_b, base_b, kl_b, thr)
                self.assertAlmostEqual(pt["cpwer"], cpw[b, t_i], places=10)
                self.assertAlmostEqual(pt["compute"], cmp_[b, t_i], places=10)
                self.assertAlmostEqual(pt["frac"], fr[b, t_i], places=10)

    def test_bootstrap_mean_equals_in_sample_mean(self) -> None:
        # For the MEAN statistic, E_bootstrap[resample mean] == sample mean
        # exactly (each resample position draws uniformly from the empirical).
        # Finite-B Monte Carlo error shrinks as 1/sqrt(B); with n=6 (high
        # per-window variance) and B=2000 the MC error is ~0.01, so we assert
        # within 0.05 (places=1) to confirm unbiasedness without flakiness.
        tiny = [1.0, 2.0, 3.0, 0.5, 1.5, 2.5]
        base = [0.4, 0.8, 1.2, 0.2, 0.6, 1.0]
        kl = [0.0, 3.5, 5.0, 1.0, 4.0, 2.0]
        thr = 3.0
        in_sample = bp.compute_pareto_point(tiny, base, kl, thr)["cpwer"]
        cpw, _, _ = bp.bootstrap_pareto_curve(
            tiny, base, kl, [thr], n_boot=2000, seed=42)
        self.assertAlmostEqual(float(cpw.mean()), in_sample, places=1)

    def test_compute_in_range(self) -> None:
        tiny = [1.0, 2.0, 3.0, 0.5]
        base = [0.4, 0.8, 1.2, 0.2]
        kl = [0.0, 3.5, 5.0, 1.0]
        _, cmp_, _ = bp.bootstrap_pareto_curve(
            tiny, base, kl, [0.0, 3.0, 6.0], n_boot=50, seed=1)
        self.assertTrue(np.all(cmp_ >= 1.0 - 1e-9))
        self.assertTrue(np.all(cmp_ <= 1.93 + 1e-9))

    def test_deterministic_with_seed(self) -> None:
        tiny = [1.0, 2.0, 3.0, 0.5]
        base = [0.4, 0.8, 1.2, 0.2]
        kl = [0.0, 3.5, 5.0, 1.0]
        a = bp.bootstrap_pareto_curve(tiny, base, kl, [0.0, 3.0], 10, 42)[0]
        b = bp.bootstrap_pareto_curve(tiny, base, kl, [0.0, 3.0], 10, 42)[0]
        np.testing.assert_array_equal(a, b)


# --------------------------------------------------------- smoke: real data
class TestSmokeRealData(unittest.TestCase):
    """Smoke tests on the real RQ43 per-window data (no full main() run)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.windows = bp.load_rq43_windows()
        cls.tiny = cls.windows["tiny_sep_cpwer"]
        cls.base = cls.windows["base_sep_cpwer"]
        cls.kl = cls.windows["kl_sep"]
        cls.curve = bp.compute_pareto_curve(
            cls.tiny, cls.base, cls.kl, bp.THRESHOLD_SWEEP)

    def test_loads_77_windows(self) -> None:
        self.assertEqual(len(self.tiny), 77)
        self.assertEqual(len(self.base), 77)
        self.assertEqual(len(self.kl), 77)

    def test_curve_has_14_points(self) -> None:
        self.assertEqual(len(self.curve), 14)

    def test_reproduces_rq43_cpwer_at_primary(self) -> None:
        pt = next(p for p in self.curve if abs(p["threshold"] - 3.30) < 1e-9)
        self.assertAlmostEqual(pt["cpwer"], 0.888947, places=4)

    def test_reproduces_rq43_compute_at_primary(self) -> None:
        pt = next(p for p in self.curve if abs(p["threshold"] - 3.30) < 1e-9)
        self.assertAlmostEqual(pt["compute"], 1.688442, places=4)

    def test_reproduces_rq43_frac_at_primary(self) -> None:
        pt = next(p for p in self.curve if abs(p["threshold"] - 3.30) < 1e-9)
        self.assertAlmostEqual(pt["frac"], 0.74026, places=4)

    def test_baseline_cpwer_is_always_tiny_separated(self) -> None:
        # always-tiny-separated mean cpWER = 1.590909 (RQ43)
        mean_tiny = sum(self.tiny) / len(self.tiny)
        self.assertAlmostEqual(mean_tiny, 1.590909, places=4)
        self.assertAlmostEqual(mean_tiny, bp.BASELINE_CPWER, places=4)

    def test_all_sweep_cpwer_below_baseline(self) -> None:
        # In-sample, every cascade point beats the always-tiny baseline on cpWER
        # (RQ43 finding). The bootstrap tests whether this is statistically robust.
        for p in self.curve:
            self.assertLess(p["cpwer"], bp.BASELINE_CPWER + 1e-9)

    def test_bootstrap_h46b_holds_at_primary(self) -> None:
        # Quick bootstrap at the primary point only: compute CI must be < 1.93.
        cpw, cmp_, _ = bp.bootstrap_pareto_curve(
            self.tiny, self.base, self.kl, [3.30], n_boot=500, seed=42)
        _, hi, _ = bp.percentile_ci(cmp_[:, 0])
        self.assertLess(hi, 1.93)


if __name__ == "__main__":
    unittest.main()
