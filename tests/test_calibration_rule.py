"""Tests for RQ48: calibration rule comparison for threshold stability
(experimental/frontier).

Pins the pure helpers: ``calibrate_youdens_j``, ``calibrate_f1``,
``calibrate_cost_aware``, ``count_modes``. Also pins ``calibrate_max_sens_at_spec``
(RQ44's baseline, delegated), module constants, and smoke-tests the in-sample
calibration on the real 77-window AISHELL-4 data: the baseline reproduces RQ44's
0.38 threshold and the cost-aware rule yields a valid threshold.

No Whisper / no audio needed. numpy + stdlib only.
"""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

# The RQ48 analysis script lives in results/frontier/ as a standalone module
# (no src. package), mirroring the RQ44 test pattern. The script itself adds
# RQ44's dir to sys.path and imports bootstrap_threshold_analysis, so here we
# only need to inject the RQ48 script dir.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_DIR = _PROJECT_ROOT / "results" / "frontier" / "calibration_rule_comparison"
sys.path.insert(0, str(_SCRIPT_DIR))

import calibration_rule_analysis as rq48  # noqa: E402  (path-injected import)

# RQ44's module is needed for the baseline-equivalence cross-check.
_RQ44_DIR = _PROJECT_ROOT / "results" / "frontier" / "bootstrap_threshold_stability"
sys.path.insert(0, str(_RQ44_DIR))
import bootstrap_threshold_analysis as rq44  # noqa: E402  (path-injected import)

AISHELL4_JSON = (
    _PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)


# --------------------------------------------------------------- youden's J
class TestCalibrateYoudensJ(unittest.TestCase):
    def test_separable_case_maximises_j(self) -> None:
        # negs 0/0.1/0.2, pos 1.0/1.1. J=1 (sens=1, spec=1) for t in (0.2, 1.0];
        # tie-break -> lowest grid point = 0.21.
        scores = np.array([0.0, 0.1, 0.2, 1.0, 1.1])
        labels = np.array([0, 0, 0, 1, 1])
        out = rq48.calibrate_youdens_j(scores, labels)
        self.assertAlmostEqual(out["threshold"], 0.21, places=6)
        self.assertEqual(out["sensitivity"], 1.0)
        self.assertEqual(out["specificity"], 1.0)
        self.assertAlmostEqual(out["youdens_j"], 1.0, places=6)

    def test_j_value_equals_sens_plus_spec_minus_one(self) -> None:
        scores = np.array([0.0, 0.3, 0.7, 1.0])
        labels = np.array([0, 0, 1, 1])
        out = rq48.calibrate_youdens_j(scores, labels)
        self.assertAlmostEqual(
            out["youdens_j"],
            out["sensitivity"] + out["specificity"] - 1.0,
            places=6,
        )

    def test_tie_break_lower_threshold(self) -> None:
        # negs 0,1 ; pos 5,6. J=1 for any t in (1.0, 5.0]; lowest grid = 1.01.
        scores = np.array([0.0, 1.0, 5.0, 6.0])
        labels = np.array([0, 0, 1, 1])
        out = rq48.calibrate_youdens_j(scores, labels)
        self.assertAlmostEqual(out["threshold"], 1.01, places=6)
        self.assertAlmostEqual(out["youdens_j"], 1.0, places=6)

    def test_empty_positives_safe(self) -> None:
        # All clean: sens=0 everywhere; J = spec - 1, maximised at high threshold
        # (spec=1). Tie-break lowest threshold with spec=1 is the first grid
        # point above the max negative score (0.5 -> 0.51).
        scores = np.array([0.0, 0.25, 0.5])
        labels = np.array([0, 0, 0])
        out = rq48.calibrate_youdens_j(scores, labels)
        self.assertEqual(out["sensitivity"], 0.0)
        self.assertEqual(out["tp"], 0)
        self.assertEqual(out["fn"], 0)
        self.assertGreaterEqual(out["specificity"], 1.0 - 1e-9)
        self.assertAlmostEqual(out["youdens_j"], 0.0, places=6)

    def test_empty_negatives_safe(self) -> None:
        # All positive: spec=1 everywhere; J = sens, maximised at low threshold
        # where all pos flagged. Lowest grid = 0.0.
        scores = np.array([0.3, 0.6, 0.9])
        labels = np.array([1, 1, 1])
        out = rq48.calibrate_youdens_j(scores, labels)
        self.assertEqual(out["sensitivity"], 1.0)
        self.assertEqual(out["specificity"], 1.0)
        self.assertAlmostEqual(out["threshold"], 0.0, places=6)

    def test_returns_all_confusion_counts(self) -> None:
        scores = np.array([0.0, 0.5, 0.9, 1.0])
        labels = np.array([0, 0, 1, 1])
        out = rq48.calibrate_youdens_j(scores, labels)
        for key in ("threshold", "sensitivity", "specificity",
                    "tp", "fp", "tn", "fn", "youdens_j"):
            self.assertIn(key, out)
        self.assertEqual(out["tp"] + out["fn"], 2)
        self.assertEqual(out["fp"] + out["tn"], 2)

    def test_j_does_not_require_specificity_boundary(self) -> None:
        # On interleaved data, RQ44's rule at target_spec=0.99 is pinned to high
        # specificity (it can only flag windows whose flagging keeps spec >= 0.99,
        # capping sensitivity). Youden's J trades specificity for sensitivity
        # continuously -- no discontinuous boundary -- so it reaches >= the
        # spec rule's sensitivity, and strictly more on this data.
        scores = np.array([0.0, 0.4, 0.6, 1.0])
        labels = np.array([0, 1, 0, 1])
        out_j = rq48.calibrate_youdens_j(scores, labels)
        out_spec = rq44.calibrate_threshold_at_spec(scores, labels, target_spec=0.99)
        self.assertGreater(out_j["sensitivity"], 0.0)
        self.assertGreaterEqual(
            out_j["sensitivity"], out_spec["sensitivity"] - 1e-9)


# --------------------------------------------------------------- F1
class TestCalibrateF1(unittest.TestCase):
    def test_separable_case_maximises_f1(self) -> None:
        scores = np.array([0.0, 0.1, 0.2, 1.0, 1.1])
        labels = np.array([0, 0, 0, 1, 1])
        out = rq48.calibrate_f1(scores, labels)
        self.assertAlmostEqual(out["threshold"], 0.21, places=6)
        self.assertEqual(out["sensitivity"], 1.0)
        self.assertAlmostEqual(out["f1"], 1.0, places=6)

    def test_f1_value_formula(self) -> None:
        scores = np.array([0.0, 0.3, 0.7, 1.0])
        labels = np.array([0, 0, 1, 1])
        out = rq48.calibrate_f1(scores, labels)
        prec = out["precision"]
        rec = out["sensitivity"]
        expected = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        self.assertAlmostEqual(out["f1"], expected, places=6)

    def test_tie_break_lower_threshold(self) -> None:
        scores = np.array([0.0, 1.0, 5.0, 6.0])
        labels = np.array([0, 0, 1, 1])
        out = rq48.calibrate_f1(scores, labels)
        self.assertAlmostEqual(out["threshold"], 1.01, places=6)
        self.assertAlmostEqual(out["f1"], 1.0, places=6)

    def test_zero_tp_gives_f1_zero(self) -> None:
        # Threshold so high nothing is flagged -> tp=0 -> F1=0.
        scores = np.array([0.0, 0.1, 0.2])
        labels = np.array([0, 0, 1])
        out = rq48.calibrate_f1(scores, labels)
        # The optimal F1 here flags the single positive (score 0.2): at t<=0.2
        # tp=1. So F1>0 is achievable; just check the reported f1 is consistent
        # with tp.
        tp = out["tp"]
        if tp == 0:
            self.assertAlmostEqual(out["f1"], 0.0, places=6)
        else:
            self.assertGreater(out["f1"], 0.0)

    def test_precision_recall_relationship(self) -> None:
        scores = np.array([0.0, 0.4, 0.6, 0.9, 1.0])
        labels = np.array([0, 0, 1, 0, 1])
        out = rq48.calibrate_f1(scores, labels)
        tp, fp, fn = out["tp"], out["fp"], out["fn"]
        prec_expected = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec_expected = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        self.assertAlmostEqual(out["precision"], prec_expected, places=6)
        self.assertAlmostEqual(out["sensitivity"], rec_expected, places=6)

    def test_returns_all_confusion_counts(self) -> None:
        scores = np.array([0.0, 0.5, 0.9, 1.0])
        labels = np.array([0, 0, 1, 1])
        out = rq48.calibrate_f1(scores, labels)
        for key in ("threshold", "sensitivity", "specificity",
                    "tp", "fp", "tn", "fn", "f1", "precision"):
            self.assertIn(key, out)
        self.assertEqual(out["tp"] + out["fn"], 2)
        self.assertEqual(out["fp"] + out["tn"], 2)


# --------------------------------------------------------------- cost-aware
class TestCalibrateCostAware(unittest.TestCase):
    def test_minimises_expected_cpwer(self) -> None:
        # Clean windows (0.1, 0.2): sep=1.0 < mixed=2.0 -> route SEPARATED.
        # Hallucinated windows (0.8, 0.9): mixed=1.0 < sep=1.5 -> route MIXED.
        # Optimal threshold in (0.2, 0.8]; lowest grid point = 0.21 -> cost 1.0.
        scores = np.array([0.1, 0.2, 0.8, 0.9])
        labels = np.array([0, 0, 1, 1])
        mixed = np.array([2.0, 2.0, 1.0, 1.0])
        sep = np.array([1.0, 1.0, 1.5, 1.5])
        out = rq48.calibrate_cost_aware(scores, labels, mixed, sep)
        self.assertAlmostEqual(out["threshold"], 0.21, places=6)
        self.assertAlmostEqual(out["expected_cpwer"], 1.0, places=6)

    def test_routes_flagged_to_mixed_unflagged_to_separated(self) -> None:
        scores = np.array([0.1, 0.9])
        labels = np.array([0, 1])
        mixed = np.array([5.0, 1.0])
        sep = np.array([1.0, 5.0])
        out = rq48.calibrate_cost_aware(scores, labels, mixed, sep)
        # Optimal: flag 0.9 (mixed 1.0), don't flag 0.1 (sep 1.0) -> cost 1.0.
        # Threshold in (0.1, 0.9]; lowest = 0.11.
        self.assertAlmostEqual(out["threshold"], 0.11, places=6)
        self.assertAlmostEqual(out["expected_cpwer"], 1.0, places=6)

    def test_tie_break_lower_threshold_when_cpwer_tied(self) -> None:
        # mixed == sep everywhere -> every threshold gives cost 1.0 -> lowest = 0.0.
        scores = np.array([0.3, 0.6, 0.9])
        labels = np.array([0, 1, 1])
        mixed = np.array([1.0, 1.0, 1.0])
        sep = np.array([1.0, 1.0, 1.0])
        out = rq48.calibrate_cost_aware(scores, labels, mixed, sep)
        self.assertAlmostEqual(out["threshold"], 0.0, places=6)
        self.assertAlmostEqual(out["expected_cpwer"], 1.0, places=6)

    def test_threshold_independent_of_labels(self) -> None:
        # The cost objective depends only on scores + cpwer, NOT labels.
        # Changing labels must not change the chosen threshold (only the
        # reported confusion counts).
        scores = np.array([0.1, 0.2, 0.8, 0.9])
        mixed = np.array([2.0, 2.0, 1.0, 1.0])
        sep = np.array([1.0, 1.0, 1.5, 1.5])
        out_a = rq48.calibrate_cost_aware(scores, np.array([0, 0, 1, 1]), mixed, sep)
        out_b = rq48.calibrate_cost_aware(scores, np.array([1, 1, 0, 0]), mixed, sep)
        self.assertAlmostEqual(out_a["threshold"], out_b["threshold"], places=6)
        self.assertAlmostEqual(out_a["expected_cpwer"], out_b["expected_cpwer"],
                               places=6)

    def test_returns_all_confusion_counts(self) -> None:
        scores = np.array([0.1, 0.5, 0.9])
        labels = np.array([0, 1, 1])
        mixed = np.array([1.5, 1.0, 1.0])
        sep = np.array([1.0, 1.5, 1.5])
        out = rq48.calibrate_cost_aware(scores, labels, mixed, sep)
        for key in ("threshold", "sensitivity", "specificity",
                    "tp", "fp", "tn", "fn", "expected_cpwer"):
            self.assertIn(key, out)
        self.assertEqual(out["tp"] + out["fn"], 2)
        self.assertEqual(out["fp"] + out["tn"], 1)

    def test_flags_all_when_mixed_always_cheaper(self) -> None:
        # mixed < sep for every window -> flag everything -> lowest threshold 0.0.
        scores = np.array([0.1, 0.5, 0.9])
        labels = np.array([0, 1, 1])
        mixed = np.array([1.0, 1.0, 1.0])
        sep = np.array([2.0, 2.0, 2.0])
        out = rq48.calibrate_cost_aware(scores, labels, mixed, sep)
        self.assertAlmostEqual(out["threshold"], 0.0, places=6)
        self.assertAlmostEqual(out["expected_cpwer"], 1.0, places=6)

    def test_flags_none_when_separated_always_cheaper(self) -> None:
        # sep < mixed for every window -> flag nothing -> highest threshold that
        # flags nothing. The lowest threshold with cost = mean(sep) is the first
        # grid point above the max score (0.9 -> 0.91).
        scores = np.array([0.1, 0.5, 0.9])
        labels = np.array([0, 1, 1])
        mixed = np.array([2.0, 2.0, 2.0])
        sep = np.array([1.0, 1.0, 1.0])
        out = rq48.calibrate_cost_aware(scores, labels, mixed, sep)
        self.assertAlmostEqual(out["threshold"], 0.91, places=6)
        self.assertAlmostEqual(out["expected_cpwer"], 1.0, places=6)


# --------------------------------------------------------------- count_modes
class TestCountModes(unittest.TestCase):
    def test_single_dominant_mode(self) -> None:
        thr = np.array([0.38] * 95 + [0.5] * 5)  # 0.5 exactly 5%
        out = rq48.count_modes(thr)
        self.assertEqual(out["n_modes"], 2)
        self.assertEqual(out["n_unique"], 2)

    def test_below_threshold_excluded(self) -> None:
        thr = np.array([0.38] * 96 + [0.5] * 4)  # 0.5 is 4% < 5%
        out = rq48.count_modes(thr)
        self.assertEqual(out["n_modes"], 1)
        self.assertEqual(out["modes"][0]["threshold"], 0.38)

    def test_empty_returns_zero(self) -> None:
        out = rq48.count_modes(np.array([]))
        self.assertEqual(out["n_modes"], 0)
        self.assertEqual(out["modes"], [])
        self.assertEqual(out["n_unique"], 0)

    def test_all_unique_all_modes(self) -> None:
        # n=4, each 25% -> all >= 5% -> 4 modes.
        thr = np.array([0.1, 0.2, 0.3, 0.4])
        out = rq48.count_modes(thr)
        self.assertEqual(out["n_modes"], 4)
        self.assertEqual(out["n_unique"], 4)

    def test_modes_sorted_by_descending_count(self) -> None:
        thr = np.array([0.38] * 60 + [0.01] * 30 + [0.33] * 10)
        out = rq48.count_modes(thr)
        self.assertEqual(out["n_modes"], 3)
        fracs = [m["fraction"] for m in out["modes"]]
        self.assertEqual(fracs, sorted(fracs, reverse=True))
        self.assertEqual(out["modes"][0]["threshold"], 0.38)
        self.assertEqual(out["modes"][1]["threshold"], 0.01)
        self.assertEqual(out["modes"][2]["threshold"], 0.33)

    def test_custom_min_fraction(self) -> None:
        thr = np.array([0.38] * 60 + [0.01] * 30 + [0.33] * 10)
        out = rq48.count_modes(thr, min_fraction=0.5)
        self.assertEqual(out["n_modes"], 1)
        self.assertEqual(out["modes"][0]["threshold"], 0.38)

    def test_boundary_exact_5pct_included(self) -> None:
        # Exactly 5% should be included (>= 5% - EPS).
        thr = np.array([0.38] * 19 + [0.5] * 1)  # 0.5 = 1/20 = 5%
        out = rq48.count_modes(thr)
        self.assertEqual(out["n_modes"], 2)

    def test_modes_carry_count_and_fraction(self) -> None:
        thr = np.array([0.38] * 60 + [0.01] * 40)
        out = rq48.count_modes(thr)
        for m in out["modes"]:
            self.assertIn("count", m)
            self.assertIn("fraction", m)
            self.assertIn("threshold", m)
        self.assertEqual(out["modes"][0]["count"], 60)
        self.assertAlmostEqual(out["modes"][0]["fraction"], 0.6, places=6)


# --------------------------------------------------------------- baseline rule
class TestCalibrateMaxSensAtSpec(unittest.TestCase):
    def test_delegates_to_rq44_exactly(self) -> None:
        scores = np.array([0.0, 0.1, 0.2, 0.15, 1.0])
        labels = np.array([0, 0, 0, 1, 1])
        a = rq48.calibrate_max_sens_at_spec(scores, labels, target_spec=2 / 3)
        b = rq44.calibrate_threshold_at_spec(scores, labels, target_spec=2 / 3)
        self.assertAlmostEqual(a["threshold"], b["threshold"], places=6)
        self.assertEqual(a["tp"], b["tp"])
        self.assertEqual(a["fp"], b["fp"])

    def test_default_target_spec_is_090(self) -> None:
        scores = np.array([0.0, 0.1, 0.2, 1.0, 1.1])
        labels = np.array([0, 0, 0, 1, 1])
        out = rq48.calibrate_max_sens_at_spec(scores, labels)
        self.assertGreaterEqual(out["specificity"], 0.90 - 1e-9)


# --------------------------------------------------------------- module constants
class TestModuleConstants(unittest.TestCase):
    def test_bootstrap_config(self) -> None:
        self.assertEqual(rq48.N_BOOT, 2000)
        self.assertEqual(rq48.SEED, 42)

    def test_min_mode_fraction(self) -> None:
        self.assertEqual(rq48.MIN_MODE_FRACTION, 0.05)

    def test_rq44_reference_values(self) -> None:
        self.assertEqual(rq48.RQ44_OOB_CPWER_MEDIAN, 1.056)
        self.assertEqual(rq48.RQ44_N_DISTINCT_THRESHOLDS, 6)

    def test_hypothesis_kill_thresholds(self) -> None:
        self.assertEqual(rq48.H48A_MAX_MODES, 3)
        self.assertEqual(rq48.H48B_MAX_MODES, 3)
        self.assertEqual(rq48.H48C_MAX_MODES, 2)
        self.assertEqual(rq48.H48C_CPWER_KILL, 1.056)

    def test_threshold_grid_matches_rq44(self) -> None:
        # Same grid as RQ44 -> thresholds directly comparable.
        self.assertEqual(rq48.THRESHOLD_GRID, rq44.THRESHOLD_GRID)
        self.assertEqual(len(rq48.THRESHOLD_GRID), 201)


# --------------------------------------------- in-sample reproduction (smoke)
@unittest.skipUnless(AISHELL4_JSON.exists(), "AISHELL-4 validation JSON not present")
class TestInSampleReproduction(unittest.TestCase):
    """Smoke tests on the real 77-window AISHELL-4 data: the baseline reproduces
    RQ44's 0.38 threshold and every rule yields a valid operating point."""

    @classmethod
    def setUpClass(cls) -> None:
        data = json.loads(AISHELL4_JSON.read_text(encoding="utf-8"))
        windows = data["windows"]
        cls.lang_ent = np.array(
            [rq48.max_across_speakers(w) for w in windows], dtype=float
        )
        cls.sep_cpwer = np.array(
            [float(w["always_separated_cpwer"]) for w in windows], dtype=float
        )
        cls.mixed_cpwer = np.array(
            [float(w["always_mixed_cpwer"]) for w in windows], dtype=float
        )
        cls.labels = (cls.sep_cpwer > 1.0).astype(int)
        cls.n = len(windows)

    def test_77_windows(self) -> None:
        self.assertEqual(self.n, 77)

    def test_baseline_threshold_is_038(self) -> None:
        out = rq48.calibrate_max_sens_at_spec(self.lang_ent, self.labels)
        self.assertAlmostEqual(out["threshold"], 0.38, places=6)

    def test_cost_aware_valid_threshold(self) -> None:
        out = rq48.calibrate_cost_aware(
            self.lang_ent, self.labels, self.mixed_cpwer, self.sep_cpwer
        )
        self.assertGreaterEqual(out["threshold"], 0.0)
        self.assertLessEqual(out["threshold"], 2.0)
        self.assertFalse(math.isnan(out["expected_cpwer"]))

    def test_all_rules_give_valid_thresholds(self) -> None:
        for cal in (rq48.calibrate_max_sens_at_spec,
                    rq48.calibrate_youdens_j,
                    rq48.calibrate_f1):
            out = cal(self.lang_ent, self.labels)
            self.assertGreaterEqual(out["threshold"], 0.0)
            self.assertLessEqual(out["threshold"], 2.0)
        out_cost = rq48.calibrate_cost_aware(
            self.lang_ent, self.labels, self.mixed_cpwer, self.sep_cpwer)
        self.assertGreaterEqual(out_cost["threshold"], 0.0)
        self.assertLessEqual(out_cost["threshold"], 2.0)


# --------------------------------------------------------------- cross-rule relationships
class TestCrossRuleRelationships(unittest.TestCase):
    def test_youdens_j_matches_baseline_on_clean_separable_data(self) -> None:
        # When the data is cleanly separable, both rules reach sens=1, spec=1.
        scores = np.array([0.0, 0.1, 0.2, 1.0, 1.1])
        labels = np.array([0, 0, 0, 1, 1])
        base = rq48.calibrate_max_sens_at_spec(scores, labels)
        j = rq48.calibrate_youdens_j(scores, labels)
        self.assertEqual(base["sensitivity"], 1.0)
        self.assertEqual(j["sensitivity"], 1.0)
        self.assertAlmostEqual(j["specificity"], 1.0, places=6)

    def test_cost_aware_in_sample_cpwer_le_baseline(self) -> None:
        # Cost-aware minimises cpWER directly, so its in-sample expected cpWER
        # cannot exceed the baseline rule's in-sample cpWER on the same data.
        scores = np.array([0.1, 0.2, 0.8, 0.9])
        labels = np.array([0, 0, 1, 1])
        mixed = np.array([2.0, 2.0, 1.0, 1.0])
        sep = np.array([1.0, 1.0, 1.5, 1.5])
        base = rq48.calibrate_max_sens_at_spec(scores, labels)
        cost = rq48.calibrate_cost_aware(scores, labels, mixed, sep)
        base_sel = np.where(scores >= base["threshold"] - 1e-9, mixed, sep).mean()
        self.assertLessEqual(cost["expected_cpwer"], base_sel + 1e-9)

    def test_youdens_and_f1_smooth_no_specificity_boundary(self) -> None:
        # On interleaved data where RQ44's rule at 0.99 spec flags nothing,
        # Youden's J and F1 both still select a non-trivial operating point
        # (sensitivity > 0) -- they have no discontinuous specificity boundary.
        scores = np.array([0.0, 0.4, 0.6, 1.0])
        labels = np.array([0, 1, 0, 1])
        j = rq48.calibrate_youdens_j(scores, labels)
        f = rq48.calibrate_f1(scores, labels)
        self.assertGreater(j["sensitivity"], 0.0)
        self.assertGreater(f["sensitivity"], 0.0)


if __name__ == "__main__":
    unittest.main()
