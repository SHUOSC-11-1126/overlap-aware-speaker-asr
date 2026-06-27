"""Tests for RQ61: shrinkage threshold calibration (experimental/frontier).

Pins the pure helpers: ``shrinkage_objective``, ``calibrate_shrinkage``,
``_summarise_lambda``, ``select_best_lambda``. Also pins the module constants,
the lam=0 ↔ RQ44 baseline equivalence (in-sample AND on a small bootstrap draw),
the shrinkage "pull toward prior" effect on synthetic Mode-S-style data, the
reuse of RQ48's ``count_modes`` and RQ44's bootstrap framework, and the
hypothesis kill-conditions (H61a/b/c). A real-data smoke test reproduces RQ44's
in-sample 0.38 threshold and 1.043 corrected cpWER.

No Whisper / no audio / no LLM needed. numpy + stdlib only.
"""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

# The RQ61 analysis script lives in results/frontier/ as a standalone module
# (no src. package), mirroring the RQ44/RQ48 test pattern.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_DIR = _PROJECT_ROOT / "results" / "frontier" / "shrinkage_threshold_calibration"
sys.path.insert(0, str(_SCRIPT_DIR))
import shrinkage_threshold_analysis as rq61  # noqa: E402  (path-injected import)

# RQ44's module is needed for the lam=0 baseline-equivalence cross-check.
_RQ44_DIR = _PROJECT_ROOT / "results" / "frontier" / "bootstrap_threshold_stability"
sys.path.insert(0, str(_RQ44_DIR))
import bootstrap_threshold_analysis as rq44  # noqa: E402  (path-injected import)

# RQ48's module is needed to verify count_modes is reused verbatim.
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


def _load_real_signals():
    """Load the 77-window AISHELL-4 signals used by RQ44/RQ48/RQ61."""
    data = json.loads(AISHELL4_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]
    lang_ent = np.array([rq44.max_across_speakers(w) for w in windows], dtype=float)
    mixed = np.array([float(w["always_mixed_cpwer"]) for w in windows], dtype=float)
    sep = np.array([float(w["always_separated_cpwer"]) for w in windows], dtype=float)
    labels = (sep > rq44.CATASTROPHIC_CPWER).astype(int)
    return lang_ent, mixed, sep, labels


# ----------------------------------------------------------- shrinkage objective
class TestShrinkageObjective(unittest.TestCase):
    def test_objective_equals_sens_minus_penalty(self) -> None:
        obj = rq61.shrinkage_objective(
            threshold=0.5, sensitivity=0.9, prior_mean=0.38, lam=0.1
        )
        self.assertAlmostEqual(obj, 0.9 - 0.1 * abs(0.5 - 0.38), places=6)

    def test_lam_zero_objective_equals_sensitivity(self) -> None:
        obj = rq61.shrinkage_objective(0.95, 0.8, 0.38, 0.0)
        self.assertAlmostEqual(obj, 0.8, places=6)

    def test_threshold_at_prior_has_zero_penalty(self) -> None:
        obj = rq61.shrinkage_objective(0.38, 0.7, 0.38, 1.0)
        self.assertAlmostEqual(obj, 0.7, places=6)

    def test_penalty_is_lam_times_abs_diff(self) -> None:
        # Two thresholds equidistant from prior (0.28 and 0.48) -> same penalty.
        o_lo = rq61.shrinkage_objective(0.28, 0.9, 0.38, 0.5)
        o_hi = rq61.shrinkage_objective(0.48, 0.9, 0.38, 0.5)
        self.assertAlmostEqual(o_lo, o_hi, places=6)

    def test_higher_lam_stronger_penalty(self) -> None:
        # Same threshold/sensitivity; larger lambda -> smaller objective.
        o_small = rq61.shrinkage_objective(0.95, 0.9, 0.38, 0.1)
        o_large = rq61.shrinkage_objective(0.95, 0.9, 0.38, 1.0)
        self.assertGreater(o_small, o_large)

    def test_farther_threshold_smaller_objective(self) -> None:
        # Same sensitivity; threshold farther from prior -> smaller objective.
        o_near = rq61.shrinkage_objective(0.40, 0.9, 0.38, 0.5)
        o_far = rq61.shrinkage_objective(0.95, 0.9, 0.38, 0.5)
        self.assertGreater(o_near, o_far)


# ----------------------------------------------------------- calibrate_shrinkage
class TestCalibrateShrinkage(unittest.TestCase):
    def test_separable_case_maximises_sensitivity(self) -> None:
        # negs 0/0.1/0.2, pos 1.0/1.1. lam=0 -> max sens at >=90% spec.
        scores = np.array([0.0, 0.1, 0.2, 1.0, 1.1])
        labels = np.array([0, 0, 0, 1, 1])
        out = rq61.calibrate_shrinkage(scores, labels, lam=0.0)
        self.assertEqual(out["sensitivity"], 1.0)
        self.assertGreaterEqual(out["specificity"], 0.9 - 1e-9)

    def test_returns_all_confusion_counts(self) -> None:
        scores = np.array([0.0, 0.5, 0.9, 1.0])
        labels = np.array([0, 0, 1, 1])
        out = rq61.calibrate_shrinkage(scores, labels, lam=0.0)
        for key in ("threshold", "sensitivity", "specificity",
                    "tp", "fp", "tn", "fn", "objective", "penalty"):
            self.assertIn(key, out)
        self.assertEqual(out["tp"] + out["fn"], 2)
        self.assertEqual(out["fp"] + out["tn"], 2)

    def test_objective_field_matches_sens_minus_penalty(self) -> None:
        scores = np.array([0.0, 0.4, 0.9, 1.0])
        labels = np.array([0, 0, 1, 1])
        out = rq61.calibrate_shrinkage(scores, labels, lam=0.5)
        expected = out["sensitivity"] - 0.5 * abs(out["threshold"] - 0.38)
        self.assertAlmostEqual(out["objective"], expected, places=6)

    def test_penalty_field_matches_lam_times_abs_diff(self) -> None:
        scores = np.array([0.0, 0.4, 0.9, 1.0])
        labels = np.array([0, 0, 1, 1])
        out = rq61.calibrate_shrinkage(scores, labels, lam=0.5)
        self.assertAlmostEqual(
            out["penalty"], 0.5 * abs(out["threshold"] - 0.38), places=6
        )

    def test_empty_positives_safe(self) -> None:
        scores = np.array([0.0, 0.25, 0.5])
        labels = np.array([0, 0, 0])
        out = rq61.calibrate_shrinkage(scores, labels, lam=0.5)
        self.assertEqual(out["sensitivity"], 0.0)
        self.assertEqual(out["tp"], 0)
        self.assertEqual(out["fn"], 0)
        self.assertGreaterEqual(out["specificity"], 1.0 - 1e-9)

    def test_empty_negatives_safe(self) -> None:
        scores = np.array([0.3, 0.6, 0.9])
        labels = np.array([1, 1, 1])
        out = rq61.calibrate_shrinkage(scores, labels, lam=0.5)
        self.assertEqual(out["sensitivity"], 1.0)
        self.assertEqual(out["specificity"], 1.0)

    def test_infeasible_falls_back_to_highest_threshold(self) -> None:
        # No threshold can reach 0.90 specificity because even the highest
        # feasible threshold flags a negative. Force target_spec=1.01 so nothing
        # is feasible -> fallback to the highest grid point.
        scores = np.array([0.0, 5.0])
        labels = np.array([0, 1])
        out = rq61.calibrate_shrinkage(scores, labels, lam=0.5, target_spec=1.01)
        self.assertEqual(out["threshold"], rq61.THRESHOLD_GRID[-1])
        self.assertEqual(out["sensitivity"], 0.0)
        self.assertEqual(out["specificity"], 1.0)

    def test_default_prior_mean_is_038(self) -> None:
        scores = np.array([0.0, 0.5, 0.9, 1.0])
        labels = np.array([0, 0, 1, 1])
        out_default = rq61.calibrate_shrinkage(scores, labels, lam=1.0)
        out_explicit = rq61.calibrate_shrinkage(
            scores, labels, lam=1.0, prior_mean=0.38
        )
        self.assertAlmostEqual(
            out_default["threshold"], out_explicit["threshold"], places=6
        )

    def test_default_target_spec_is_090(self) -> None:
        scores = np.array([0.0, 0.5, 0.9, 1.0])
        labels = np.array([0, 0, 1, 1])
        out_default = rq61.calibrate_shrinkage(scores, labels, lam=0.0)
        out_explicit = rq61.calibrate_shrinkage(
            scores, labels, lam=0.0, target_spec=0.90
        )
        self.assertAlmostEqual(
            out_default["threshold"], out_explicit["threshold"], places=6
        )

    def test_grid_default_is_threshold_grid(self) -> None:
        scores = np.array([0.0, 0.5, 0.9, 1.0])
        labels = np.array([0, 0, 1, 1])
        out_default = rq61.calibrate_shrinkage(scores, labels, lam=0.0)
        out_explicit = rq61.calibrate_shrinkage(
            scores, labels, lam=0.0, grid=rq61.THRESHOLD_GRID
        )
        self.assertAlmostEqual(
            out_default["threshold"], out_explicit["threshold"], places=6
        )


# ----------------------------------------------------- lam=0 ↔ RQ44 equivalence
class TestLamZeroEquivalence(unittest.TestCase):
    """lam=0 (no shrinkage) must reproduce RQ44's calibrate_threshold_at_spec
    exactly: max sensitivity at >= 90% specificity, tie-break higher specificity
    then lowest threshold."""

    def test_lam_zero_matches_rq44_on_real_data(self) -> None:
        lang_ent, _, _, labels = _load_real_signals()
        out_shr = rq61.calibrate_shrinkage(lang_ent, labels, lam=0.0)
        out_rq44 = rq44.calibrate_threshold_at_spec(lang_ent, labels)
        self.assertAlmostEqual(out_shr["threshold"], out_rq44["threshold"], places=6)
        self.assertAlmostEqual(out_shr["sensitivity"], out_rq44["sensitivity"], places=6)
        self.assertAlmostEqual(out_shr["specificity"], out_rq44["specificity"], places=6)
        self.assertEqual(out_shr["tp"], out_rq44["tp"])
        self.assertEqual(out_shr["fp"], out_rq44["fp"])

    def test_lam_zero_matches_rq44_real_threshold_038(self) -> None:
        lang_ent, _, _, labels = _load_real_signals()
        out = rq61.calibrate_shrinkage(lang_ent, labels, lam=0.0)
        self.assertAlmostEqual(out["threshold"], 0.38, places=6)

    def test_lam_zero_matches_rq44_on_synthetic_separable(self) -> None:
        scores = np.array([0.0, 0.1, 0.2, 1.0, 1.1])
        labels = np.array([0, 0, 0, 1, 1])
        out_shr = rq61.calibrate_shrinkage(scores, labels, lam=0.0)
        out_rq44 = rq44.calibrate_threshold_at_spec(scores, labels)
        self.assertAlmostEqual(out_shr["threshold"], out_rq44["threshold"], places=6)

    def test_lam_zero_matches_rq44_on_synthetic_overlapping(self) -> None:
        # Overlapping scores where the specificity boundary matters.
        scores = np.array([0.0, 0.35, 0.37, 0.39, 0.40, 0.42, 0.95, 1.0])
        labels = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        out_shr = rq61.calibrate_shrinkage(scores, labels, lam=0.0)
        out_rq44 = rq44.calibrate_threshold_at_spec(scores, labels)
        self.assertAlmostEqual(out_shr["threshold"], out_rq44["threshold"], places=6)
        self.assertAlmostEqual(out_shr["sensitivity"], out_rq44["sensitivity"], places=6)

    def test_lam_zero_matches_rq44_on_synthetic_tie_break(self) -> None:
        # All hall have very high entropy -> many thresholds tie on sensitivity;
        # tie-break must match RQ44 (higher spec, then lower threshold).
        scores = np.array([0.0, 0.1, 0.5, 0.6, 5.0, 5.0])
        labels = np.array([0, 0, 0, 0, 1, 1])
        out_shr = rq61.calibrate_shrinkage(scores, labels, lam=0.0)
        out_rq44 = rq44.calibrate_threshold_at_spec(scores, labels)
        self.assertAlmostEqual(out_shr["threshold"], out_rq44["threshold"], places=6)

    def test_lam_zero_matches_rq44_on_small_bootstrap(self) -> None:
        # Stronger: lam=0 matches RQ44 on every resample of a small bootstrap.
        lang_ent, _, _, labels = _load_real_signals()
        n = len(lang_ent)
        boot_idx = rq44.bootstrap_indices(n, 50, 42)  # B=50 (fast)
        for b in range(50):
            idx = boot_idx[b]
            out_shr = rq61.calibrate_shrinkage(lang_ent[idx], labels[idx], lam=0.0)
            out_rq44 = rq44.calibrate_threshold_at_spec(lang_ent[idx], labels[idx])
            self.assertAlmostEqual(
                out_shr["threshold"], out_rq44["threshold"], places=6,
                msg=f"mismatch at bootstrap b={b}"
            )
            self.assertAlmostEqual(
                out_shr["sensitivity"], out_rq44["sensitivity"], places=6,
                msg=f"sens mismatch at b={b}"
            )


# --------------------------------------------------- shrinkage "pull" effect
class TestShrinkagePullTowardPrior(unittest.TestCase):
    """Shrinkage with lam>0 pulls the threshold toward the prior (0.38)."""

    def _mode_s_synthetic(self):
        # 2 low-entropy hallucinated (Mode S, score 0.02), 35 high-entropy hall
        # (5.0), 40 clean (0.0). At t=0.01: flags 0.02 & 5.0 -> sens=1.0, spec=1.0.
        # At t=0.38: flags only 5.0 -> sens=35/37, spec=1.0.
        scores = np.concatenate([
            np.full(2, 0.02), np.full(35, 5.0), np.zeros(40),
        ])
        labels = np.concatenate([np.ones(37), np.zeros(40)])
        return scores, labels

    def test_lam_zero_picks_low_threshold_mode_s(self) -> None:
        scores, labels = self._mode_s_synthetic()
        out = rq61.calibrate_shrinkage(scores, labels, lam=0.0)
        self.assertLess(out["threshold"], 0.1)
        self.assertAlmostEqual(out["sensitivity"], 1.0, places=6)

    def test_large_lam_pulls_to_prior(self) -> None:
        scores, labels = self._mode_s_synthetic()
        out = rq61.calibrate_shrinkage(scores, labels, lam=1.0)
        self.assertAlmostEqual(out["threshold"], 0.38, places=6)

    def test_intermediate_lam_between_low_and_prior(self) -> None:
        scores, labels = self._mode_s_synthetic()
        out_lo = rq61.calibrate_shrinkage(scores, labels, lam=0.0)
        out_mid = rq61.calibrate_shrinkage(scores, labels, lam=0.5)
        out_hi = rq61.calibrate_shrinkage(scores, labels, lam=1.0)
        # Monotone pull: threshold(0.0) <= threshold(0.5) <= threshold(1.0).
        self.assertLessEqual(out_lo["threshold"], out_mid["threshold"] + 1e-9)
        self.assertLessEqual(out_mid["threshold"], out_hi["threshold"] + 1e-9)

    def test_shrinkage_does_not_violate_specificity_constraint(self) -> None:
        # The shrinkage-chosen threshold must still satisfy >= 90% specificity.
        scores, labels = self._mode_s_synthetic()
        for lam in rq61.LAMBDAS:
            out = rq61.calibrate_shrinkage(scores, labels, lam=lam)
            self.assertGreaterEqual(
                out["specificity"], 0.90 - 1e-9,
                msg=f"spec<0.90 at lam={lam}"
            )

    def test_shrinkage_pulls_high_threshold_toward_prior(self) -> None:
        # Construct a case where lam=0 tie-breaks to a high threshold (the only
        # feasible point), but a lower feasible point exists with slightly lower
        # sensitivity. Shrinkage trades the sensitivity gap for the prior penalty.
        # 1 clean at 0.45 (causes 0.38 to be infeasible if it is the only neg
        # above 0.38). Use: negs 0.0, 0.45 ; pos 0.5, 0.5, 0.5, 5.0.
        # t=0.46: flags 0.5,0.5,0.5,5.0 -> sens=1.0, spec=1.0 (0.0,0.45 not flagged)
        # t=0.38: flags 0.45(clean!),0.5,0.5,0.5,5.0 -> sens=1.0, spec=1/2=0.5 infeasible
        # So 0.38 infeasible; lowest feasible max-sens is 0.46. lam=0 picks 0.46.
        # Shrinkage cannot pick 0.38 (infeasible) but among feasible thresholds
        # [0.46, 5.0] it picks the one closest to 0.38 subject to the objective.
        scores = np.array([0.0, 0.45, 0.5, 0.5, 0.5, 5.0])
        labels = np.array([0, 0, 1, 1, 1, 1])
        out_zero = rq61.calibrate_shrinkage(scores, labels, lam=0.0)
        out_high = rq61.calibrate_shrinkage(scores, labels, lam=1.0)
        # lam=0 picks 0.46 (lowest feasible max-sens). Shrinkage keeps it close
        # to 0.38 within the feasible set -> still 0.46 (no closer feasible point
        # with equal sensitivity). Verify shrinkage never picks an infeasible t.
        self.assertGreaterEqual(out_high["specificity"], 0.90 - 1e-9)
        self.assertLessEqual(out_high["threshold"], out_zero["threshold"] + 1e-9)


# ----------------------------------------------------------- _summarise_lambda
class TestSummariseLambda(unittest.TestCase):
    def test_summary_has_threshold_distribution_keys(self) -> None:
        thr = np.array([0.38, 0.38, 0.01, 0.87])
        oob = np.array([1.04, 1.04, 1.10, 1.17])
        s = rq61._summarise_lambda(thr, oob)
        td = s["threshold_distribution"]
        for key in ("median", "mean", "std", "percentile_2_5", "percentile_97_5",
                    "interval_width", "n_unique", "n_modes_5pct", "modes_5pct"):
            self.assertIn(key, td)

    def test_summary_has_oob_cpwer_distribution_keys(self) -> None:
        thr = np.array([0.38, 0.38, 0.01])
        oob = np.array([1.04, 1.05, 1.10])
        s = rq61._summarise_lambda(thr, oob)
        od = s["oob_cpwer_distribution"]
        for key in ("median", "mean", "percentile_2_5", "percentile_97_5",
                    "frac_below_rq44_median"):
            self.assertIn(key, od)

    def test_summary_median_threshold(self) -> None:
        thr = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        oob = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
        s = rq61._summarise_lambda(thr, oob)
        self.assertAlmostEqual(s["threshold_distribution"]["median"], 0.3, places=6)

    def test_summary_interval_width(self) -> None:
        # 100 elements: 50 at 0.01, 50 at 0.95. The 2.5/97.5 percentiles land
        # exactly on the endpoints (no interpolation), so width = 0.94.
        thr = np.array([0.01] * 50 + [0.95] * 50)
        oob = np.array([1.0] * 100)
        s = rq61._summarise_lambda(thr, oob)
        self.assertAlmostEqual(
            s["threshold_distribution"]["interval_width"], 0.94, places=6
        )

    def test_summary_n_modes_uses_count_modes(self) -> None:
        # 0.38 appears 60% (mode), 0.01 appears 30% (mode), 0.87 10% (not a mode
        # at 5% threshold... 10% >= 5% so it IS a mode). 3 modes.
        thr = np.array([0.38] * 60 + [0.01] * 30 + [0.87] * 10)
        oob = np.array([1.0] * 100)
        s = rq61._summarise_lambda(thr, oob)
        self.assertEqual(s["threshold_distribution"]["n_modes_5pct"], 3)

    def test_summary_handles_nan_oob(self) -> None:
        # Some resamples may have empty OOB -> nan cpWER. Summary must drop them.
        thr = np.array([0.38, 0.38, 0.01])
        oob = np.array([1.04, float("nan"), 1.10])
        s = rq61._summarise_lambda(thr, oob)
        od = s["oob_cpwer_distribution"]
        self.assertEqual(od["n_valid"], 2)
        self.assertAlmostEqual(od["median"], 1.07, places=6)

    def test_summary_oob_median(self) -> None:
        thr = np.array([0.38, 0.38, 0.01])
        oob = np.array([1.00, 1.04, 1.10])
        s = rq61._summarise_lambda(thr, oob)
        self.assertAlmostEqual(s["oob_cpwer_distribution"]["median"], 1.04, places=6)

    def test_summary_frac_below_rq44_median(self) -> None:
        thr = np.array([0.38, 0.38, 0.01, 0.87])
        oob = np.array([1.00, 1.04, 1.10, 1.17])  # 2 of 4 below 1.056
        s = rq61._summarise_lambda(thr, oob)
        self.assertAlmostEqual(
            s["oob_cpwer_distribution"]["frac_below_rq44_median"], 0.5, places=6
        )


# ----------------------------------------------------------- select_best_lambda
class TestSelectBestLambda(unittest.TestCase):
    def _summary(self, n_modes, width, oob_median, lam):
        return {
            "lambda": lam,
            "n_modes_5pct": n_modes,
            "interval_width": width,
            "oob_cpwer_median": oob_median,
        }

    def test_picks_deployable_fewest_modes(self) -> None:
        per = {
            "0.0": self._summary(5, 0.94, 1.056, 0.0),
            "0.5": self._summary(2, 0.50, 1.050, 0.5),  # deployable, 2 modes
            "1.0": self._summary(1, 0.40, 1.060, 1.0),  # NOT deployable (1.060>1.056)
        }
        best = rq61.select_best_lambda(per)
        self.assertEqual(best["lambda"], 0.5)

    def test_tiebreak_narrowest_width(self) -> None:
        per = {
            "0.5": self._summary(2, 0.50, 1.050, 0.5),
            "1.0": self._summary(2, 0.30, 1.050, 1.0),  # same modes, narrower
        }
        best = rq61.select_best_lambda(per)
        self.assertEqual(best["lambda"], 1.0)

    def test_tiebreak_smallest_lambda(self) -> None:
        per = {
            "0.1": self._summary(2, 0.40, 1.050, 0.1),
            "0.5": self._summary(2, 0.40, 1.050, 0.5),  # same modes & width
        }
        best = rq61.select_best_lambda(per)
        self.assertEqual(best["lambda"], 0.1)

    def test_no_deployable_picks_closest_oob(self) -> None:
        per = {
            "0.0": self._summary(5, 0.94, 1.080, 0.0),
            "1.0": self._summary(2, 0.40, 1.058, 1.0),  # closest to 1.056
        }
        best = rq61.select_best_lambda(per)
        self.assertEqual(best["lambda"], 1.0)

    def test_returns_reason_field(self) -> None:
        per = {"0.5": self._summary(2, 0.50, 1.050, 0.5)}
        best = rq61.select_best_lambda(per)
        self.assertIn("reason", best)
        self.assertIn("all_hypotheses_supported", best)

    def test_deployability_threshold_is_1056(self) -> None:
        per = {
            "0.5": self._summary(2, 0.50, 1.056, 0.5),  # exactly 1.056 -> deployable
        }
        best = rq61.select_best_lambda(per)
        self.assertEqual(best["lambda"], 0.5)


# ----------------------------------------------------------- count_modes reuse
class TestCountModesReuse(unittest.TestCase):
    def test_count_modes_is_rq48_function(self) -> None:
        self.assertIs(rq61.count_modes, rq48.count_modes)

    def test_count_modes_returns_n_modes(self) -> None:
        thr = np.array([0.38] * 60 + [0.01] * 30 + [0.87] * 10)
        out = rq61.count_modes(thr, min_fraction=0.05)
        self.assertEqual(out["n_modes"], 3)

    def test_count_modes_min_fraction_filter(self) -> None:
        thr = np.array([0.38] * 90 + [0.01] * 5 + [0.87] * 5)  # 5% each
        out = rq61.count_modes(thr, min_fraction=0.05)
        self.assertEqual(out["n_modes"], 3)
        out2 = rq61.count_modes(thr, min_fraction=0.06)
        self.assertEqual(out2["n_modes"], 1)

    def test_count_modes_empty(self) -> None:
        out = rq61.count_modes(np.array([]), min_fraction=0.05)
        self.assertEqual(out["n_modes"], 0)


# ----------------------------------------------------- bootstrap framework reuse
class TestBootstrapFrameworkReuse(unittest.TestCase):
    def test_bootstrap_indices_is_rq44_function(self) -> None:
        self.assertIs(rq61.bootstrap_indices, rq44.bootstrap_indices)

    def test_out_of_bag_cpwer_is_rq44_function(self) -> None:
        self.assertIs(rq61.out_of_bag_cpwer, rq44.out_of_bag_cpwer)

    def test_max_across_speakers_is_rq44_function(self) -> None:
        self.assertIs(rq61.max_across_speakers, rq44.max_across_speakers)

    def test_percentile_interval_is_rq44_function(self) -> None:
        self.assertIs(rq61.percentile_interval, rq44.percentile_interval)

    def test_bootstrap_indices_deterministic(self) -> None:
        a = rq61.bootstrap_indices(77, 100, 42)
        b = rq61.bootstrap_indices(77, 100, 42)
        np.testing.assert_array_equal(a, b)

    def test_bootstrap_indices_shape(self) -> None:
        idx = rq61.bootstrap_indices(77, 100, 42)
        self.assertEqual(idx.shape, (100, 77))

    def test_oob_cpwer_routing(self) -> None:
        # flag = score >= threshold -> MIXED; else SEPARATED.
        scores = np.array([0.0, 0.5, 0.9, 1.0])
        mixed = np.array([1.0, 1.0, 1.2, 1.3])
        sep = np.array([0.5, 1.5, 0.6, 1.6])
        # OOB = windows not in in_bag_idx. in_bag = {0,1}; OOB = {2,3}.
        # threshold 0.55 -> flags 0.9,1.0 -> MIXED (1.2,1.3); OOB mean = 1.25.
        out = rq61.out_of_bag_cpwer(scores, mixed, sep, 0.55, np.array([0, 1]))
        self.assertAlmostEqual(out["cpwer"], 1.25, places=6)
        self.assertEqual(out["n_oob"], 2)

    def test_paired_bootstrap_same_indices_across_lambdas(self) -> None:
        # RQ61 draws ONE bootstrap index array and reuses for all lambdas.
        # Verify the draw matches RQ44's (same seed/shape) -> lam=0 reproduces
        # RQ44's first resample's threshold.
        lang_ent, mixed, sep, labels = _load_real_signals()
        n = len(lang_ent)
        boot_idx = rq61.bootstrap_indices(n, 10, 42)
        # lam=0 threshold on resample 0 should match RQ44's calibrate on the
        # same resample.
        idx = boot_idx[0]
        thr_shr = rq61.calibrate_shrinkage(lang_ent[idx], labels[idx], lam=0.0)["threshold"]
        thr_rq44 = rq44.calibrate_threshold_at_spec(lang_ent[idx], labels[idx])["threshold"]
        self.assertAlmostEqual(thr_shr, thr_rq44, places=6)


# ----------------------------------------------------------- module constants
class TestModuleConstants(unittest.TestCase):
    def test_prior_mean_is_038(self) -> None:
        self.assertAlmostEqual(rq61.PRIOR_MEAN, 0.38, places=6)

    def test_lambdas_set(self) -> None:
        self.assertEqual(rq61.LAMBDAS, [0.0, 0.01, 0.1, 0.5, 1.0])

    def test_n_boot_is_10000(self) -> None:
        self.assertEqual(rq61.N_BOOT, 10000)

    def test_seed_is_42(self) -> None:
        self.assertEqual(rq61.SEED, 42)

    def test_target_specificity_is_090(self) -> None:
        self.assertAlmostEqual(rq61.TARGET_SPECIFICITY, 0.90, places=6)

    def test_min_mode_fraction_is_005(self) -> None:
        self.assertAlmostEqual(rq61.MIN_MODE_FRACTION, 0.05, places=6)

    def test_rq44_reference_oob_cpwer(self) -> None:
        self.assertAlmostEqual(rq61.RQ44_OOB_CPWER_MEDIAN, 1.056, places=6)

    def test_rq44_reference_n_unique(self) -> None:
        self.assertEqual(rq61.RQ44_N_UNIQUE, 6)

    def test_rq44_reference_interval_width(self) -> None:
        self.assertAlmostEqual(rq61.RQ44_INTERVAL_WIDTH, 0.94, places=6)

    def test_h61a_max_modes_is_2(self) -> None:
        self.assertEqual(rq61.H61A_MAX_MODES, 2)

    def test_h61b_max_cpwer_is_1056(self) -> None:
        self.assertAlmostEqual(rq61.H61B_MAX_CPWER, 1.056, places=6)

    def test_h61c_max_width_is_094(self) -> None:
        self.assertAlmostEqual(rq61.H61C_MAX_WIDTH, 0.94, places=6)

    def test_threshold_grid_matches_rq44(self) -> None:
        self.assertEqual(rq61.THRESHOLD_GRID, rq44.THRESHOLD_GRID)

    def test_eps_matches_rq44(self) -> None:
        self.assertEqual(rq61.EPS, rq44.EPS)

    def test_catastrophic_cpwer_matches_rq44(self) -> None:
        self.assertEqual(rq61.CATASTROPHIC_CPWER, rq44.CATASTROPHIC_CPWER)


# ------------------------------------------------------- hypothesis kill conditions
class TestHypothesisKillConditions(unittest.TestCase):
    def test_h61a_kill_if_more_than_2_modes(self) -> None:
        # H61a: <= 2 modes supported; > 2 killed.
        self.assertTrue(rq61._h61a_supported(2))
        self.assertTrue(rq61._h61a_supported(1))
        self.assertFalse(rq61._h61a_supported(3))
        self.assertFalse(rq61._h61a_supported(6))

    def test_h61b_kill_if_oob_above_1056(self) -> None:
        # H61b: OOB <= 1.056 supported; > 1.056 killed.
        self.assertTrue(rq61._h61b_supported(1.050))
        self.assertTrue(rq61._h61b_supported(1.056))  # boundary: <= supported
        self.assertFalse(rq61._h61b_supported(1.057))
        self.assertFalse(rq61._h61b_supported(1.10))

    def test_h61c_kill_if_width_at_least_094(self) -> None:
        # H61c: width < 0.94 supported; >= 0.94 killed.
        self.assertTrue(rq61._h61c_supported(0.50))
        self.assertTrue(rq61._h61c_supported(0.939))
        self.assertFalse(rq61._h61c_supported(0.94))
        self.assertFalse(rq61._h61c_supported(0.95))

    def test_rq44_baseline_kills_all_three(self) -> None:
        # RQ44's pooled stats: 5 modes (>=5%), OOB 1.056, width 0.94.
        # H61a: 5 > 2 -> killed. H61b: 1.056 <= 1.056 -> supported (boundary).
        # H61c: 0.94 >= 0.94 -> killed.
        self.assertFalse(rq61._h61a_supported(5))
        self.assertTrue(rq61._h61b_supported(1.056))
        self.assertFalse(rq61._h61c_supported(0.94))


# ----------------------------------------------------------- real-data smoke
class TestRealDataSmoke(unittest.TestCase):
    def test_loads_77_windows(self) -> None:
        lang_ent, _, _, labels = _load_real_signals()
        self.assertEqual(len(lang_ent), 77)
        self.assertEqual(len(labels), 77)

    def test_label_counts_match_rq44(self) -> None:
        _, _, _, labels = _load_real_signals()
        self.assertEqual(int(labels.sum()), 37)
        self.assertEqual(int((labels == 0).sum()), 40)

    def test_lam_zero_in_sample_threshold_038(self) -> None:
        lang_ent, _, _, labels = _load_real_signals()
        out = rq61.calibrate_shrinkage(lang_ent, labels, lam=0.0)
        self.assertAlmostEqual(out["threshold"], 0.38, places=6)

    def test_lam_zero_in_sample_cpwer_1043(self) -> None:
        lang_ent, mixed, sep, labels = _load_real_signals()
        out = rq61.calibrate_shrinkage(lang_ent, labels, lam=0.0)
        flag = lang_ent >= out["threshold"] - rq61.EPS
        selected = np.where(flag, mixed, sep)
        self.assertAlmostEqual(float(selected.mean()), 1.043290, places=4)

    def test_all_lambdas_produce_valid_threshold_on_real_data(self) -> None:
        lang_ent, _, _, labels = _load_real_signals()
        for lam in rq61.LAMBDAS:
            out = rq61.calibrate_shrinkage(lang_ent, labels, lam=lam)
            self.assertGreaterEqual(out["threshold"], 0.0)
            self.assertLessEqual(out["threshold"], 2.0)
            self.assertGreaterEqual(out["specificity"], 0.90 - 1e-9,
                                    msg=f"spec<0.90 at lam={lam}")

    def test_shrinkage_threshold_within_grid(self) -> None:
        lang_ent, _, _, labels = _load_real_signals()
        grid_set = set(rq61.THRESHOLD_GRID)
        for lam in rq61.LAMBDAS:
            out = rq61.calibrate_shrinkage(lang_ent, labels, lam=lam)
            self.assertIn(round(out["threshold"], 2), grid_set)


if __name__ == "__main__":
    unittest.main()
