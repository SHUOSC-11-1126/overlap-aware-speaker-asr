"""Tests for RQ51: hybrid calibration rule for the corrected router
(experimental/frontier).

Pins the pure helpers: ``_asymmetric_cost``, ``calibrate_hybrid`` (the two-step
F1 + cost-aware-with-asymmetric-cost rule), module constants, and the in-sample
calibration on the real 77-window AISHELL-4 data. Also smoke-tests the
bootstrap aggregation at small B and pins the hypothesis verdicts against the
committed JSON.

No Whisper / no audio needed. numpy + stdlib only.
"""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

# The RQ51 analysis script lives in results/frontier/ as a standalone module
# (no src. package), mirroring the RQ44/RQ48 test pattern. The script itself
# adds RQ44's and RQ48's dirs to sys.path and imports them, so here we only
# need to inject the RQ51 script dir.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_DIR = _PROJECT_ROOT / "results" / "frontier" / "hybrid_calibration_rule"
sys.path.insert(0, str(_SCRIPT_DIR))

import hybrid_calibration_analysis as rq51  # noqa: E402  (path-injected import)

# RQ48's module is needed for the F1-equivalence cross-check.
_RQ48_DIR = _PROJECT_ROOT / "results" / "frontier" / "calibration_rule_comparison"
sys.path.insert(0, str(_RQ48_DIR))
import calibration_rule_analysis as rq48  # noqa: E402  (path-injected import)

AISHELL4_JSON = (
    _PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
RESULTS_JSON = (
    _SCRIPT_DIR / "hybrid_calibration_results.json"
)


# --------------------------------------------------------------- constants
class TestModuleConstants(unittest.TestCase):
    """Pin the module constants so the hybrid rule's parameters are fixed."""

    def test_bootstrap_size_is_10000(self) -> None:
        self.assertEqual(rq51.N_BOOT, 10000)

    def test_seed_is_42(self) -> None:
        self.assertEqual(rq51.SEED,42)

    def test_min_mode_fraction_is_5pct(self) -> None:
        self.assertEqual(rq51.MIN_MODE_FRACTION, 0.05)

    def test_neighborhood_is_0p10(self) -> None:
        self.assertEqual(rq51.NEIGHBORHOOD, 0.10)

    def test_catastrophic_oob_is_1p10(self) -> None:
        self.assertEqual(rq51.CATASTROPHIC_OOB, 1.10)

    def test_penalty_is_2p0(self) -> None:
        self.assertEqual(rq51.PENALTY, 2.0)

    def test_threshold_grid_matches_rq44(self) -> None:
        self.assertEqual(rq51.THRESHOLD_GRID, rq48.THRESHOLD_GRID)
        self.assertEqual(len(rq51.THRESHOLD_GRID), 201)
        self.assertAlmostEqual(rq51.THRESHOLD_GRID[0], 0.00, places=6)
        self.assertAlmostEqual(rq51.THRESHOLD_GRID[-1], 2.00, places=6)

    def test_rq48_reference_values_pinned(self) -> None:
        self.assertEqual(rq51.RQ48_F1_N_MODES, 2)
        self.assertAlmostEqual(rq51.RQ48_F1_WIDTH, 0.94, places=6)
        self.assertAlmostEqual(rq51.RQ48_COST_WIDTH, 0.32, places=6)
        self.assertAlmostEqual(rq51.RQ48_COST_OOB_MEDIAN, 1.0632, places=4)
        self.assertAlmostEqual(rq51.RQ44_OOB_CPWER_MEDIAN, 1.056, places=3)

    def test_hypothesis_kill_thresholds(self) -> None:
        self.assertEqual(rq51.H51A_MAX_MODES, 2)
        self.assertAlmostEqual(rq51.H51B_MAX_WIDTH, 0.32, places=6)
        self.assertAlmostEqual(rq51.H51C_CPWER_KILL, 1.056, places=3)

    def test_framework_imports_from_rq44(self) -> None:
        # The detector, bootstrap, and OOB evaluator must be RQ44's exact
        # functions (identity check, not just equality).
        import bootstrap_threshold_analysis as rq44
        self.assertIs(rq51.max_across_speakers, rq44.max_across_speakers)
        self.assertIs(rq51.bootstrap_indices, rq44.bootstrap_indices)
        self.assertIs(rq51.out_of_bag_cpwer, rq44.out_of_bag_cpwer)

    def test_helpers_imported_from_rq48(self) -> None:
        # calibrate_f1, count_modes must be RQ48's exact functions.
        self.assertIs(rq51.calibrate_f1, rq48.calibrate_f1)
        self.assertIs(rq51.count_modes, rq48.count_modes)


# --------------------------------------------------------------- _asymmetric_cost
class TestAsymmetricCost(unittest.TestCase):
    """Pin the asymmetric expected-cpWER cost."""

    def test_all_below_catastrophic_equals_mean(self) -> None:
        # No window exceeds 1.10 -> weights all 1 -> cost == mean.
        arr = np.array([1.0, 1.02, 1.05, 1.09])
        cost = rq51._asymmetric_cost(arr, catastrophic=1.10, penalty=2.0)
        self.assertAlmostEqual(cost, float(arr.mean()), places=6)

    def test_all_above_catastrophic_equals_penalty_weighted_mean(self) -> None:
        # All windows exceed 1.10 -> weights all `penalty` -> cost == mean
        # (penalty cancels because every weight is the same).
        arr = np.array([1.12, 1.15, 1.20])
        cost = rq51._asymmetric_cost(arr, catastrophic=1.10, penalty=2.0)
        self.assertAlmostEqual(cost, float(arr.mean()), places=6)

    def test_mixed_weights_correctly(self) -> None:
        # 2 below (weight 1), 2 above (weight 2). cost = (1.0 + 1.05 + 2*1.15 + 2*1.20) / 6
        arr = np.array([1.0, 1.05, 1.15, 1.20])
        cost = rq51._asymmetric_cost(arr, catastrophic=1.10, penalty=2.0)
        expected = (1.0 + 1.05 + 2 * 1.15 + 2 * 1.20) / (1 + 1 + 2 + 2)
        self.assertAlmostEqual(cost, expected, places=6)

    def test_penalty_scales_above_threshold_only(self) -> None:
        # Increasing penalty raises the cost when any window is above.
        arr = np.array([1.0, 1.20])
        c2 = rq51._asymmetric_cost(arr, catastrophic=1.10, penalty=2.0)
        c5 = rq51._asymmetric_cost(arr, catastrophic=1.10, penalty=5.0)
        self.assertGreater(c5, c2)

    def test_penalty_does_not_affect_all_below(self) -> None:
        arr = np.array([1.0, 1.05])
        c2 = rq51._asymmetric_cost(arr, catastrophic=1.10, penalty=2.0)
        c10 = rq51._asymmetric_cost(arr, catastrophic=1.10, penalty=10.0)
        self.assertAlmostEqual(c2, c10, places=6)

    def test_empty_array_returns_nan(self) -> None:
        cost = rq51._asymmetric_cost(np.array([]), catastrophic=1.10, penalty=2.0)
        self.assertTrue(math.isnan(cost))

    def test_single_window_below(self) -> None:
        cost = rq51._asymmetric_cost(np.array([1.0]), catastrophic=1.10, penalty=2.0)
        self.assertAlmostEqual(cost, 1.0, places=6)

    def test_single_window_above(self) -> None:
        cost = rq51._asymmetric_cost(np.array([1.20]), catastrophic=1.10, penalty=3.0)
        self.assertAlmostEqual(cost, 1.20, places=6)

    def test_boundary_excluded_below(self) -> None:
        # cpWER == catastrophic (1.10) is NOT > catastrophic -> weight 1.
        arr = np.array([1.10, 1.20])
        cost = rq51._asymmetric_cost(arr, catastrophic=1.10, penalty=2.0)
        expected = (1.10 + 2 * 1.20) / 3
        self.assertAlmostEqual(cost, expected, places=6)

    def test_removing_penalty_entirely_lowers_cost(self) -> None:
        # Raising the catastrophic threshold ABOVE all values removes the
        # penalty entirely -> cost collapses to the plain mean (which is lower
        # than the penalty-weighted cost when some windows were above).
        arr = np.array([1.0, 1.15, 1.20])
        c_some_above = rq51._asymmetric_cost(arr, catastrophic=1.10, penalty=5.0)
        c_none_above = rq51._asymmetric_cost(arr, catastrophic=1.25, penalty=5.0)
        self.assertLess(c_none_above, c_some_above)
        self.assertAlmostEqual(c_none_above, float(arr.mean()), places=6)


# --------------------------------------------------------------- calibrate_hybrid
class TestCalibrateHybrid(unittest.TestCase):
    """Pin the two-step hybrid calibration rule."""

    def test_f1_step_matches_rq48_calibrate_f1(self) -> None:
        # The hybrid's f1_threshold must equal RQ48's calibrate_f1 output.
        scores = np.array([0.0, 0.1, 0.2, 1.0, 1.1])
        labels = np.array([0, 0, 0, 1, 1])
        mixed = np.array([1.0, 1.0, 1.0, 0.9, 0.9])
        sep = np.array([1.0, 1.0, 1.0, 1.5, 1.5])
        out = rq51.calibrate_hybrid(scores, labels, mixed, sep)
        f1_only = rq48.calibrate_f1(scores, labels)
        self.assertAlmostEqual(out["f1_threshold"], f1_only["threshold"], places=6)

    def test_threshold_within_neighborhood(self) -> None:
        # The hybrid threshold must lie within [f1_thr - 0.1, f1_thr + 0.1].
        scores = np.array([0.0, 0.1, 0.2, 1.0, 1.1])
        labels = np.array([0, 0, 0, 1, 1])
        mixed = np.array([1.0, 1.0, 1.0, 0.9, 0.9])
        sep = np.array([1.0, 1.0, 1.0, 1.5, 1.5])
        out = rq51.calibrate_hybrid(scores, labels, mixed, sep)
        lo = out["f1_threshold"] - rq51.NEIGHBORHOOD
        hi = out["f1_threshold"] + rq51.NEIGHBORHOOD
        self.assertGreaterEqual(out["threshold"], lo - rq51.EPS)
        self.assertLessEqual(out["threshold"], hi + rq51.EPS)

    def test_neighborhood_bounds_reported(self) -> None:
        scores = np.array([0.0, 0.5, 1.0])
        labels = np.array([0, 0, 1])
        mixed = np.array([1.0, 1.0, 0.9])
        sep = np.array([1.0, 1.0, 1.5])
        out = rq51.calibrate_hybrid(scores, labels, mixed, sep)
        self.assertEqual(len(out["neighborhood"]), 2)
        self.assertAlmostEqual(
            out["neighborhood"][0], out["f1_threshold"] - rq51.NEIGHBORHOOD, places=6
        )
        self.assertAlmostEqual(
            out["neighborhood"][1], out["f1_threshold"] + rq51.NEIGHBORHOOD, places=6
        )

    def test_n_neighborhood_grid_positive(self) -> None:
        scores = np.array([0.0, 0.5, 1.0])
        labels = np.array([0, 0, 1])
        mixed = np.array([1.0, 1.0, 0.9])
        sep = np.array([1.0, 1.0, 1.5])
        out = rq51.calibrate_hybrid(scores, labels, mixed, sep)
        self.assertGreater(out["n_neighborhood_grid"], 0)

    def test_returns_all_confusion_counts(self) -> None:
        scores = np.array([0.0, 0.2, 0.8, 1.0])
        labels = np.array([0, 0, 1, 1])
        mixed = np.array([1.0, 1.0, 0.9, 0.9])
        sep = np.array([1.0, 1.0, 1.5, 1.5])
        out = rq51.calibrate_hybrid(scores, labels, mixed, sep)
        for k in ("tp", "fp", "tn", "fn"):
            self.assertIn(k, out)
            self.assertIsInstance(out[k], int)
        self.assertEqual(out["tp"] + out["fn"], int(labels.sum()))
        self.assertEqual(out["fp"] + out["tn"], int((labels == 0).sum()))

    def test_returns_sens_spec_in_unit_interval(self) -> None:
        scores = np.array([0.0, 0.2, 0.8, 1.0])
        labels = np.array([0, 0, 1, 1])
        mixed = np.array([1.0, 1.0, 0.9, 0.9])
        sep = np.array([1.0, 1.0, 1.5, 1.5])
        out = rq51.calibrate_hybrid(scores, labels, mixed, sep)
        self.assertGreaterEqual(out["sensitivity"], 0.0)
        self.assertLessEqual(out["sensitivity"], 1.0)
        self.assertGreaterEqual(out["specificity"], 0.0)
        self.assertLessEqual(out["specificity"], 1.0)

    def test_tie_break_lowest_threshold(self) -> None:
        # When the asymmetric cost is tied across the neighbourhood, the hybrid
        # must pick the LOWEST threshold (RQ44/RQ48 convention). Construct a
        # case where mixed == sep everywhere (cost is constant).
        scores = np.array([0.0, 0.5, 1.0])
        labels = np.array([0, 0, 1])
        mixed = np.array([1.0, 1.0, 1.0])
        sep = np.array([1.0, 1.0, 1.0])
        out = rq51.calibrate_hybrid(scores, labels, mixed, sep)
        lo = out["f1_threshold"] - rq51.NEIGHBORHOOD
        # Lowest grid point in the neighbourhood.
        grid = np.array(rq51.THRESHOLD_GRID)
        nb = grid[(grid >= lo - rq51.EPS)]
        self.assertAlmostEqual(out["threshold"], float(nb[0]), places=6)

    def test_asymmetric_cost_avoids_overflagging(self) -> None:
        # A clean window where MIXED gives cpWER > 1.10 (catastrophic) but
        # SEPARATED gives cpWER = 1.0. A low threshold would flag it MIXED
        # (catastrophic, penalised); a higher threshold keeps it SEPARATED.
        # The hybrid should prefer the higher threshold within the F1
        # neighbourhood to avoid the catastrophic penalty.
        # scores: 1 clean (0.0), 1 hallucinated (0.5). F1-optimal picks a
        # threshold in (0.0, 0.5]; within the neighbourhood the cost-aware
        # step should keep the clean window SEPARATED.
        scores = np.array([0.0, 0.5])
        labels = np.array([0, 1])
        # Clean window: MIXED catastrophic (1.20), SEPARATED good (1.0).
        # Hallucinated window: MIXED good (0.9), SEPARATED bad (1.5).
        mixed = np.array([1.20, 0.90])
        sep = np.array([1.00, 1.50])
        out = rq51.calibrate_hybrid(scores, labels, mixed, sep)
        # The clean window must NOT be flagged (threshold > 0.0) so it stays
        # SEPARATED (cpWER 1.0, not the catastrophic 1.20).
        self.assertGreater(out["threshold"], 0.0 + rq51.EPS)
        # Confirm: at the chosen threshold the clean window (score 0.0) is
        # unflagged -> SEPARATED.
        self.assertLess(0.0, out["threshold"] - rq51.EPS)

    def test_penalty_parameter_changes_behaviour(self) -> None:
        # A higher penalty should make the hybrid MORE averse to catastrophic
        # outcomes (higher threshold to avoid flagging the catastrophic clean
        # window). Use the same setup as test_asymmetric_cost_avoids_overflagging.
        scores = np.array([0.0, 0.5])
        labels = np.array([0, 1])
        mixed = np.array([1.20, 0.90])
        sep = np.array([1.00, 1.50])
        out_low_p = rq51.calibrate_hybrid(scores, labels, mixed, sep, penalty=1.0)
        out_high_p = rq51.calibrate_hybrid(scores, labels, mixed, sep, penalty=10.0)
        # With a high penalty the hybrid should flag the clean window LESS
        # (threshold >= the low-penalty threshold).
        self.assertGreaterEqual(
            out_high_p["threshold"], out_low_p["threshold"] - rq51.EPS
        )

    def test_neighborhood_parameter_shrinks_range(self) -> None:
        # A smaller neighbourhood restricts the hybrid threshold closer to f1.
        scores = np.array([0.0, 0.2, 0.8, 1.0])
        labels = np.array([0, 0, 1, 1])
        mixed = np.array([1.0, 1.0, 0.9, 0.9])
        sep = np.array([1.0, 1.0, 1.5, 1.5])
        out_wide = rq51.calibrate_hybrid(scores, labels, mixed, sep, neighborhood=0.2)
        out_narrow = rq51.calibrate_hybrid(scores, labels, mixed, sep, neighborhood=0.01)
        # Narrow neighbourhood: threshold must be within 0.01 of f1_threshold.
        self.assertLessEqual(
            abs(out_narrow["threshold"] - out_narrow["f1_threshold"]),
            0.01 + rq51.EPS,
        )
        # Wide neighbourhood has at least as many grid points as narrow.
        self.assertGreaterEqual(
            out_wide["n_neighborhood_grid"], out_narrow["n_neighborhood_grid"]
        )

    def test_empty_positives_safe(self) -> None:
        # All clean: F1 = 0 everywhere (no positives), so F1 tie-breaks to the
        # lowest threshold (0.0). The hybrid then flags all clean windows
        # (false positives). This is correct behaviour -- with no positives to
        # guide F1, the hybrid cannot identify a meaningful operating point.
        # The test pins that the call is safe and returns a valid threshold
        # within the F1 neighbourhood.
        scores = np.array([0.0, 0.25, 0.5])
        labels = np.array([0, 0, 0])
        mixed = np.array([1.0, 1.0, 1.0])
        sep = np.array([1.0, 1.0, 1.0])
        out = rq51.calibrate_hybrid(scores, labels, mixed, sep)
        self.assertEqual(out["tp"], 0)
        self.assertEqual(out["fn"], 0)
        # F1 with no positives picks threshold 0.0 (lowest tie-break).
        self.assertAlmostEqual(out["f1_threshold"], 0.0, places=6)
        # Hybrid threshold must be within the neighbourhood of 0.0.
        self.assertGreaterEqual(out["threshold"], 0.0 - rq51.NEIGHBORHOOD - rq51.EPS)
        self.assertLessEqual(out["threshold"], 0.0 + rq51.NEIGHBORHOOD + rq51.EPS)

    def test_empty_negatives_safe(self) -> None:
        # All hallucinated.
        scores = np.array([0.3, 0.6, 0.9])
        labels = np.array([1, 1, 1])
        mixed = np.array([0.9, 0.9, 0.9])
        sep = np.array([1.5, 1.5, 1.5])
        out = rq51.calibrate_hybrid(scores, labels, mixed, sep)
        self.assertEqual(out["fp"], 0)
        self.assertEqual(out["tn"], 0)
        self.assertGreaterEqual(out["sensitivity"], 0.0)

    def test_asymmetric_cost_reported(self) -> None:
        scores = np.array([0.0, 0.5, 1.0])
        labels = np.array([0, 0, 1])
        mixed = np.array([1.0, 1.0, 0.9])
        sep = np.array([1.0, 1.0, 1.5])
        out = rq51.calibrate_hybrid(scores, labels, mixed, sep)
        self.assertIn("asymmetric_cost", out)
        self.assertGreater(out["asymmetric_cost"], 0.0)

    def test_f1_metric_reported(self) -> None:
        scores = np.array([0.0, 0.2, 0.8, 1.0])
        labels = np.array([0, 0, 1, 1])
        mixed = np.array([1.0, 1.0, 0.9, 0.9])
        sep = np.array([1.0, 1.0, 1.5, 1.5])
        out = rq51.calibrate_hybrid(scores, labels, mixed, sep)
        self.assertIn("f1", out)
        self.assertGreaterEqual(out["f1"], 0.0)
        self.assertLessEqual(out["f1"], 1.0)

    def test_custom_grid_used(self) -> None:
        # A coarse custom grid must be respected.
        scores = np.array([0.0, 0.5, 1.0])
        labels = np.array([0, 0, 1])
        mixed = np.array([1.0, 1.0, 0.9])
        sep = np.array([1.0, 1.0, 1.5])
        coarse = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        out = rq51.calibrate_hybrid(scores, labels, mixed, sep, grid=coarse)
        self.assertIn(out["threshold"], [round(x, 6) for x in coarse])

    def test_output_threshold_on_grid(self) -> None:
        scores = np.array([0.0, 0.2, 0.8, 1.0])
        labels = np.array([0, 0, 1, 1])
        mixed = np.array([1.0, 1.0, 0.9, 0.9])
        sep = np.array([1.0, 1.0, 1.5, 1.5])
        out = rq51.calibrate_hybrid(scores, labels, mixed, sep)
        grid_set = {round(x, 6) for x in rq51.THRESHOLD_GRID}
        self.assertIn(round(out["threshold"], 6), grid_set)


# --------------------------------------------------------------- in-sample smoke
class TestInSampleOnAISHELL4(unittest.TestCase):
    """Smoke-test the in-sample hybrid calibration on the real 77-window data."""

    @classmethod
    def setUpClass(cls) -> None:
        if not AISHELL4_JSON.exists():
            raise unittest.SkipTest(f"AISHELL-4 JSON not found: {AISHELL4_JSON}")
        data = json.loads(AISHELL4_JSON.read_text(encoding="utf-8"))
        windows = data["windows"]
        cls.n = len(windows)
        cls.lang_ent = np.array(
            [rq51.max_across_speakers(w) for w in windows], dtype=float
        )
        cls.mixed = np.array(
            [float(w["always_mixed_cpwer"]) for w in windows], dtype=float
        )
        cls.sep = np.array(
            [float(w["always_separated_cpwer"]) for w in windows], dtype=float
        )
        cls.labels = (cls.sep > rq51.CATASTROPHIC_CPWER).astype(int)
        cls.cal = rq51.calibrate_hybrid(cls.lang_ent, cls.labels, cls.mixed, cls.sep)

    def test_n_windows_is_77(self) -> None:
        self.assertEqual(self.n, 77)

    def test_n_hallucinated_is_37(self) -> None:
        self.assertEqual(int(self.labels.sum()), 37)

    def test_n_clean_is_40(self) -> None:
        self.assertEqual(int((self.labels == 0).sum()), 40)

    def test_f1_threshold_matches_rq48(self) -> None:
        # RQ48's F1 in-sample threshold on the 77 windows = 0.38.
        self.assertAlmostEqual(self.cal["f1_threshold"], 0.38, places=6)

    def test_hybrid_threshold_within_neighborhood_of_0p38(self) -> None:
        # F1 picks 0.38; neighbourhood [0.28, 0.48]; hybrid must be in there.
        self.assertGreaterEqual(self.cal["threshold"], 0.28 - rq51.EPS)
        self.assertLessEqual(self.cal["threshold"], 0.48 + rq51.EPS)

    def test_hybrid_threshold_is_0p33(self) -> None:
        # The cost-aware step within [0.28, 0.48] picks 0.33 (the lowest
        # cpWER-tied threshold, matching RQ48's cost-aware in-sample pick).
        self.assertAlmostEqual(self.cal["threshold"], 0.33, places=6)

    def test_expected_cpwer_matches_rq48(self) -> None:
        # In-sample corrected cpWER = 1.0433 (matches RQ25/RQ44/RQ48).
        flag = self.lang_ent >= self.cal["threshold"] - rq51.EPS
        selected = np.where(flag, self.mixed, self.sep)
        self.assertAlmostEqual(float(selected.mean()), 1.04329, places=4)

    def test_sensitivity_is_high(self) -> None:
        # 35/37 hallucinated windows flagged (sens ~ 0.946).
        self.assertGreaterEqual(self.cal["sensitivity"], 0.9)


# --------------------------------------------------------------- bootstrap smoke
class TestBootstrapSmoke(unittest.TestCase):
    """Small-B smoke test of the bootstrap aggregation pipeline."""

    def test_small_b_produces_valid_summary(self) -> None:
        # Run B=50 to keep runtime < 1s; verify the summary shape matches
        # RQ48's _summarise_rule output.
        data = json.loads(AISHELL4_JSON.read_text(encoding="utf-8"))
        windows = data["windows"]
        n = len(windows)
        lang_ent = np.array(
            [rq51.max_across_speakers(w) for w in windows], dtype=float
        )
        mixed = np.array(
            [float(w["always_mixed_cpwer"]) for w in windows], dtype=float
        )
        sep = np.array(
            [float(w["always_separated_cpwer"]) for w in windows], dtype=float
        )
        labels = (sep > rq51.CATASTROPHIC_CPWER).astype(int)
        b = 50
        boot_idx = rq51.bootstrap_indices(n, b, rq51.SEED)
        thr = np.empty(b, dtype=float)
        oob = np.empty(b, dtype=float)
        for i in range(b):
            idx = boot_idx[i]
            cal = rq51.calibrate_hybrid(
                lang_ent[idx], labels[idx], mixed[idx], sep[idx]
            )
            thr[i] = cal["threshold"]
            r = rq51.out_of_bag_cpwer(lang_ent, mixed, sep, cal["threshold"], idx)
            oob[i] = r["cpwer"]
        summary = rq51._summarise_hybrid(thr, oob)
        td = summary["threshold_distribution"]
        od = summary["oob_cpwer_distribution"]
        self.assertIn("n_modes_5pct", td)
        self.assertIn("interval_width", td)
        self.assertIn("median", od)
        # All thresholds must be on the grid.
        grid_set = {round(x, 6) for x in rq51.THRESHOLD_GRID}
        for t in thr:
            self.assertIn(round(float(t), 6), grid_set)
        # OOB cpWER must be >= 1.0 (cpWER is a ratio; 1.0 = no change).
        valid = oob[~np.isnan(oob)]
        self.assertTrue(np.all(valid >= 1.0 - 1e-9))

    def test_bootstrap_deterministic_with_seed(self) -> None:
        # Same seed -> same first resample indices.
        idx1 = rq51.bootstrap_indices(77, 10, 42)
        idx2 = rq51.bootstrap_indices(77, 10, 42)
        np.testing.assert_array_equal(idx1, idx2)


# --------------------------------------------------------------- count_modes reuse
class TestCountModesReuse(unittest.TestCase):
    """Verify count_modes is RQ48's helper and behaves identically."""

    def test_single_mode(self) -> None:
        thr = np.array([0.38] * 100)
        m = rq51.count_modes(thr, 0.05)
        self.assertEqual(m["n_modes"], 1)
        self.assertAlmostEqual(m["modes"][0]["threshold"], 0.38, places=6)

    def test_two_modes_at_5pct_boundary(self) -> None:
        # 0.38 at 60%, 0.01 at 30%, 0.95 at 4% (below 5% -> not a mode).
        thr = np.array([0.38] * 60 + [0.01] * 30 + [0.95] * 4 + [0.38] * 6)
        m = rq51.count_modes(thr, 0.05)
        self.assertEqual(m["n_modes"], 2)

    def test_empty_input(self) -> None:
        m = rq51.count_modes(np.array([]), 0.05)
        self.assertEqual(m["n_modes"], 0)


# --------------------------------------------------------------- results JSON pin
class TestResultsJsonPin(unittest.TestCase):
    """Pin the committed results JSON so regressions are caught."""

    @classmethod
    def setUpClass(cls) -> None:
        if not RESULTS_JSON.exists():
            raise unittest.SkipTest(f"Results JSON not found: {RESULTS_JSON}")
        cls.data = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))

    def test_label_is_experimental_frontier(self) -> None:
        self.assertEqual(self.data["label"], "experimental/frontier")

    def test_n_windows_77(self) -> None:
        self.assertEqual(self.data["n_windows"], 77)

    def test_bootstrap_is_10000(self) -> None:
        self.assertEqual(self.data["bootstrap"]["n_boot"], 10000)
        self.assertEqual(self.data["bootstrap"]["seed"], 42)

    def test_hybrid_thresholds_length_10000(self) -> None:
        self.assertEqual(len(self.data["per_bootstrap"]["thresholds"]), 10000)
        self.assertEqual(len(self.data["per_bootstrap"]["oob_cpwer"]), 10000)

    def test_f1_thresholds_length_10000(self) -> None:
        self.assertEqual(len(self.data["per_bootstrap"]["f1_thresholds"]), 10000)

    def test_h51a_verdict_killed(self) -> None:
        # The hybrid produces 3 modes (0.33, 0.01, 0.28) > 2 -> KILLED.
        v = self.data["hypothesis_verdicts"]["H51a"]
        self.assertFalse(v["supported"])
        self.assertGreater(v["n_modes_5pct"], 2)

    def test_h51b_verdict_killed(self) -> None:
        # Width 0.84 >= 0.32 -> KILLED.
        v = self.data["hypothesis_verdicts"]["H51b"]
        self.assertFalse(v["supported"])
        self.assertGreaterEqual(v["interval_width"], 0.32)

    def test_h51c_verdict_killed(self) -> None:
        # Median OOB cpWER 1.0705 > 1.056 -> KILLED.
        v = self.data["hypothesis_verdicts"]["H51c"]
        self.assertFalse(v["supported"])
        self.assertGreater(v["median_oob_cpwer"], 1.056)

    def test_comparison_table_has_5_rows(self) -> None:
        # RQ48's 4 rules + the hybrid.
        self.assertEqual(len(self.data["rq48_comparison"]), 5)

    def test_hybrid_overfits_in_comparison(self) -> None:
        row = [r for r in self.data["rq48_comparison"] if "hybrid" in r["rule"]][0]
        self.assertTrue(row["over_fits"])

    def test_in_sample_f1_threshold_0p38(self) -> None:
        self.assertAlmostEqual(
            self.data["in_sample_calibration"]["f1_threshold"], 0.38, places=6
        )

    def test_in_sample_hybrid_threshold_in_neighborhood(self) -> None:
        isam = self.data["in_sample_calibration"]
        lo, hi = isam["neighborhood"]
        self.assertGreaterEqual(isam["threshold"], lo - 1e-9)
        self.assertLessEqual(isam["threshold"], hi + 1e-9)

    def test_modes_include_0p01(self) -> None:
        # The 0.01 "Mode S catch" mode must persist (RQ48's fundamental
        # detector ambiguity).
        modes = self.data["hybrid_summary"]["threshold_distribution"]["modes_5pct"]
        thrs = [round(m["threshold"], 6) for m in modes]
        self.assertIn(0.01, thrs)


if __name__ == "__main__":
    unittest.main()
