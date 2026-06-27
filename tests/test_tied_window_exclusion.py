"""Tests for RQ50 tied-window exclusion corrected-router (experimental/frontier).

Pin the PURE helpers used by
``results/frontier/tied_window_exclusion/tied_window_exclusion_analysis.py``:
``is_tied_window``, ``identify_tied_windows``, ``identify_nontied_windows``,
``corrected_router_decision``, ``per_window_corrected_cpwer``,
``build_per_window_rows``, plus the bootstrap helpers
(``bootstrap_indices``, ``bootstrap_distribution``, ``percentile_ci``,
``_jackknife_means``, ``bca_ci``, ``paired_delta_distribution``,
``paired_delta_ci``). Synthetic data for the pure-helper tests; the
end-to-end ``run()`` smoke tests load the real AISHELL-4 JSON (read-only)
and pin the verified tie count (35), non-tied count (42), corrected cpWER
on non-tied windows, BCa CI, and the three pre-registered hypothesis
verdicts.

Note on the tie count: RQ47's operational definition
``abs(always_mixed_cpwer - always_separated_cpwer) < 1e-6`` yields 35 tied
windows on the 77-window AISHELL-4 file. The 35/42 split is analytically
meaningful and matches the pre-registered hypotheses.
"""
from __future__ import annotations

import json
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
    / "tied_window_exclusion"
)
sys.path.insert(0, str(SCRIPT_DIR))

from tied_window_exclusion_analysis import (  # noqa: E402
    ALPHA,
    LANG_ID_ENTROPY_THRESHOLD,
    N_BOOT,
    RQ39_WORD_LEVEL_BCA_CI,
    RQ39_WORD_LEVEL_BCA_WIDTH,
    RQ39_WORD_LEVEL_CORRECTED_CPWER,
    RQ39_WORD_LEVEL_ORACLE_CPWER,
    SEED,
    TIE_TOL,
    _jackknife_means,
    bca_ci,
    bootstrap_distribution,
    bootstrap_indices,
    build_per_window_rows,
    corrected_router_decision,
    identify_nontied_windows,
    identify_tied_windows,
    is_tied_window,
    language_id_entropy,
    max_across_speakers,
    paired_delta_ci,
    paired_delta_distribution,
    per_window_corrected_cpwer,
    percentile_ci,
    run,
    script_category,
)

SOURCE_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)


def _win(
    window_id: int,
    mixed_cpwer: float,
    sep_cpwer: float,
    oracle_cpwer: float = 1.0,
    sep_texts: dict | None = None,
    num_speakers: int = 2,
    overlap_label: str = "NoOverlap",
    router_v2_method: str = "separated",
) -> dict:
    """Build a minimal synthetic window with the fields the analysis reads."""
    if sep_texts is None:
        sep_texts = {"s1": "你好", "s2": "世界"} if num_speakers >= 2 else {"s1": "你好"}
    return {
        "window_id": window_id,
        "always_mixed_cpwer": mixed_cpwer,
        "always_separated_cpwer": sep_cpwer,
        "oracle_best_cpwer": oracle_cpwer,
        "num_speakers": num_speakers,
        "overlap_label": overlap_label,
        "router_v2_method": router_v2_method,
        "separated_text_per_speaker": sep_texts,
        "ref_text_per_speaker": sep_texts,
    }


# --------------------------------------------------------------- script_category
class TestScriptCategory(unittest.TestCase):
    def test_whitespace_is_space(self) -> None:
        self.assertEqual(script_category(" "), "Space")
        self.assertEqual(script_category("\n"), "Space")

    def test_han(self) -> None:
        self.assertEqual(script_category("你"), "Han")

    def test_latin(self) -> None:
        self.assertEqual(script_category("A"), "Latin")


# ----------------------------------------------------------- language_id_entropy
class TestLanguageIdEntropy(unittest.TestCase):
    def test_empty_is_zero(self) -> None:
        self.assertEqual(language_id_entropy(""), 0.0)
        self.assertEqual(language_id_entropy("   "), 0.0)

    def test_pure_han_is_zero_entropy(self) -> None:
        self.assertAlmostEqual(language_id_entropy("你好世界你好"), 0.0, places=12)

    def test_mixed_scripts_higher_entropy(self) -> None:
        h_pure = language_id_entropy("你好你好")
        h_mixed = language_id_entropy("你好abc你好")
        self.assertGreater(h_mixed, h_pure)


# ------------------------------------------------------------ max_across_speakers
class TestMaxAcrossSpeakers(unittest.TestCase):
    def test_empty_speakers_is_zero(self) -> None:
        # window with no speaker tracks -> 0.0 (detector not tripped).
        window = {"separated_text_per_speaker": {}}
        self.assertEqual(max_across_speakers(window, lambda t: 1.0), 0.0)

    def test_max_of_multiple_speakers(self) -> None:
        # speaker 2 mixes scripts -> higher entropy than pure-Han speaker 1.
        texts = {"s1": "你好你好", "s2": "你好abc你好"}
        window = {"separated_text_per_speaker": texts}
        v = max_across_speakers(window, language_id_entropy)
        self.assertEqual(v, language_id_entropy("你好abc你好"))

    def test_skips_empty_speakers(self) -> None:
        # None / whitespace / empty strings are effectively skipped.
        texts = {"s1": "", "s2": "   ", "s3": "你好abc"}
        window = {"separated_text_per_speaker": texts}
        v = max_across_speakers(window, language_id_entropy)
        self.assertEqual(v, language_id_entropy("你好abc"))


# ---------------------------------------------------------- is_tied_window
class TestIsTiedWindow(unittest.TestCase):
    def test_equal_cpwers_is_tied(self) -> None:
        w = _win(0, 1.0, 1.0)
        self.assertTrue(is_tied_window(w))

    def test_different_cpwers_is_not_tied(self) -> None:
        w = _win(0, 1.0, 2.0)
        self.assertFalse(is_tied_window(w))

    def test_tolerance_respected(self) -> None:
        # difference > tol -> not tied
        w = _win(0, 1.0, 1.0 + 1e-5)
        self.assertFalse(is_tied_window(w, tol=1e-6))

    def test_tolerance_inclusive(self) -> None:
        # difference < tol -> tied
        w = _win(0, 1.0, 1.0 + 1e-9)
        self.assertTrue(is_tied_window(w, tol=1e-6))


# ---------------------------------------------------------- identify_tied_windows
class TestIdentifyTiedWindows(unittest.TestCase):
    def test_synthetic_returns_tied_ids(self) -> None:
        ws = [
            _win(0, 1.0, 1.0),       # tied
            _win(1, 1.0, 2.0),       # not tied
            _win(2, 1.3333333, 1.3333334),  # tied within tol
        ]
        self.assertEqual(identify_tied_windows(ws), [0, 2])

    def test_returns_window_ids_not_indices(self) -> None:
        ws = [_win(10, 1.0, 1.0), _win(20, 1.0, 2.0)]
        self.assertEqual(identify_tied_windows(ws), [10])

    def test_smoke_aishell4_tied_count_is_35(self) -> None:
        with open(SOURCE_JSON, encoding="utf-8") as f:
            data = json.load(f)
        tied = identify_tied_windows(data["windows"])
        self.assertEqual(len(tied), 35)
        self.assertEqual(len(data["windows"]), 77)

    def test_smoke_aishell4_nontied_count_is_42(self) -> None:
        with open(SOURCE_JSON, encoding="utf-8") as f:
            data = json.load(f)
        nontied = identify_nontied_windows(data["windows"])
        self.assertEqual(len(nontied), 42)


# --------------------------------------------------------- identify_nontied_windows
class TestIdentifyNontiedWindows(unittest.TestCase):
    def test_synthetic_returns_nontied_ids(self) -> None:
        ws = [
            _win(0, 1.0, 1.0),       # tied
            _win(1, 1.0, 2.0),       # not tied
            _win(2, 1.3333333, 1.3333334),  # tied within tol
        ]
        self.assertEqual(identify_nontied_windows(ws), [1])

    def test_tied_plus_nontied_partition(self) -> None:
        ws = [_win(i, 1.0, 1.0 + (i % 2)) for i in range(10)]
        tied = set(identify_tied_windows(ws))
        nontied = set(identify_nontied_windows(ws))
        self.assertEqual(tied | nontied, {w["window_id"] for w in ws})
        self.assertEqual(tied & nontied, set())


# ------------------------------------------------------- corrected_router_decision
class TestCorrectedRouterDecision(unittest.TestCase):
    def test_high_entropy_routes_to_mixed(self) -> None:
        w = _win(0, 1.0, 2.0, sep_texts={"s1": "你好abc你好"})
        self.assertEqual(corrected_router_decision(w), "mixed")

    def test_low_entropy_routes_to_separated(self) -> None:
        w = _win(0, 1.0, 2.0, sep_texts={"s1": "你好你好"})
        self.assertEqual(corrected_router_decision(w), "separated")

    def test_empty_separated_routes_to_separated(self) -> None:
        # empty separated -> entropy 0 -> below threshold -> separated
        w = _win(0, 1.0, 2.0, sep_texts={"s1": ""})
        self.assertEqual(corrected_router_decision(w), "separated")

    def test_smoke_aishell4_decision_counts_match_rq16(self) -> None:
        # lang-id alone at threshold 0.38 == threshold 0.409 on this data:
        # mixed=38, separated=39 (RQ39 reported mixed=38, separated=39).
        with open(SOURCE_JSON, encoding="utf-8") as f:
            data = json.load(f)
        decisions = [corrected_router_decision(w) for w in data["windows"]]
        self.assertEqual(sum(1 for d in decisions if d == "mixed"), 38)
        self.assertEqual(sum(1 for d in decisions if d == "separated"), 39)


# --------------------------------------------------- per_window_corrected_cpwer
class TestPerWindowCorrectedCpwer(unittest.TestCase):
    def test_mixed_decision_returns_mixed_cpwer(self) -> None:
        w = _win(0, 1.5, 2.5, sep_texts={"s1": "你好abc你好"})  # high entropy -> mixed
        self.assertEqual(per_window_corrected_cpwer(w), 1.5)

    def test_separated_decision_returns_separated_cpwer(self) -> None:
        w = _win(0, 1.5, 2.5, sep_texts={"s1": "你好你好"})  # low entropy -> separated
        self.assertEqual(per_window_corrected_cpwer(w), 2.5)

    def test_smoke_aishell4_all_windows_mean_reproduces_rq39(self) -> None:
        with open(SOURCE_JSON, encoding="utf-8") as f:
            data = json.load(f)
        corrected = np.array(
            [per_window_corrected_cpwer(w) for w in data["windows"]]
        )
        self.assertAlmostEqual(corrected.mean(), 1.04329, places=5)


# ------------------------------------------------------------- build_per_window_rows
class TestBuildPerWindowRows(unittest.TestCase):
    def test_returns_row_per_window(self) -> None:
        ws = [_win(0, 1.0, 1.0), _win(1, 1.0, 2.0)]
        rows = build_per_window_rows(ws)
        self.assertEqual(len(rows), 2)

    def test_row_has_expected_keys(self) -> None:
        rows = build_per_window_rows([_win(0, 1.0, 1.0)])
        for key in [
            "window_id", "overlap_label", "num_speakers", "lang_id_entropy",
            "corrected_decision", "always_mixed_cpwer", "always_separated_cpwer",
            "corrected_cpwer", "oracle_best_cpwer", "is_tied",
        ]:
            self.assertIn(key, rows[0])

    def test_tied_flag_set_correctly(self) -> None:
        ws = [_win(0, 1.0, 1.0), _win(1, 1.0, 2.0)]
        rows = build_per_window_rows(ws)
        self.assertTrue(rows[0]["is_tied"])
        self.assertFalse(rows[1]["is_tied"])

    def test_corrected_cpwer_follows_decision(self) -> None:
        # high-entropy window -> mixed decision -> mixed cpwer
        w = _win(0, 1.5, 2.5, sep_texts={"s1": "你好abc你好"})
        rows = build_per_window_rows([w])
        self.assertEqual(rows[0]["corrected_cpwer"], 1.5)
        self.assertEqual(rows[0]["corrected_decision"], "mixed")

    def test_smoke_aishell4_rows_count_77(self) -> None:
        with open(SOURCE_JSON, encoding="utf-8") as f:
            data = json.load(f)
        rows = build_per_window_rows(data["windows"])
        self.assertEqual(len(rows), 77)
        self.assertEqual(sum(1 for r in rows if r["is_tied"]), 35)


# ----------------------------------------------------------- bootstrap_indices
class TestBootstrapIndices(unittest.TestCase):
    def test_shape(self) -> None:
        idx = bootstrap_indices(10, 50, seed=42)
        self.assertEqual(idx.shape, (50, 10))

    def test_indices_in_range(self) -> None:
        idx = bootstrap_indices(10, 50, seed=42)
        self.assertTrue(np.all(idx >= 0))
        self.assertTrue(np.all(idx < 10))

    def test_deterministic_with_seed(self) -> None:
        a = bootstrap_indices(10, 50, seed=42)
        b = bootstrap_indices(10, 50, seed=42)
        np.testing.assert_array_equal(a, b)


# ----------------------------------------------------------- bootstrap_distribution
class TestBootstrapDistribution(unittest.TestCase):
    def test_mean_of_distribution_close_to_sample_mean(self) -> None:
        rng = np.random.default_rng(0)
        vals = rng.normal(1.0, 0.1, size=100)
        dist = bootstrap_distribution(vals, N_BOOT, SEED)
        self.assertAlmostEqual(dist.mean(), vals.mean(), places=2)

    def test_deterministic_with_seed(self) -> None:
        vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        a = bootstrap_distribution(vals, 100, 42)
        b = bootstrap_distribution(vals, 100, 42)
        np.testing.assert_array_equal(a, b)

    def test_length_matches_n_boot(self) -> None:
        vals = np.array([1.0, 2.0, 3.0])
        dist = bootstrap_distribution(vals, 100, 42)
        self.assertEqual(len(dist), 100)


# --------------------------------------------------------------- percentile_ci
class TestPercentileCi(unittest.TestCase):
    def test_basic_ci_bounds(self) -> None:
        dist = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0])
        lo, hi = percentile_ci(dist, alpha=0.05)
        self.assertLessEqual(lo, hi)
        # 2.5% and 97.5% percentiles of [0..9]
        self.assertAlmostEqual(lo, np.percentile(dist, 2.5))
        self.assertAlmostEqual(hi, np.percentile(dist, 97.5))

    def test_constant_distribution(self) -> None:
        dist = np.array([1.5] * 100)
        lo, hi = percentile_ci(dist)
        self.assertAlmostEqual(lo, 1.5)
        self.assertAlmostEqual(hi, 1.5)


# ---------------------------------------------------------------- _jackknife_means
class TestJackknifeMeans(unittest.TestCase):
    def test_length_matches_input(self) -> None:
        vals = np.array([1.0, 2.0, 3.0, 4.0])
        jack = _jackknife_means(vals)
        self.assertEqual(len(jack), 4)

    def test_leave_one_out_identity(self) -> None:
        vals = np.array([1.0, 2.0, 3.0, 4.0])
        jack = _jackknife_means(vals)
        # leave out 1.0 -> mean(2,3,4)=3.0; leave out 2 -> mean(1,3,4)=8/3; etc.
        self.assertAlmostEqual(jack[0], 3.0)
        self.assertAlmostEqual(jack[1], (1 + 3 + 4) / 3.0)

    def test_single_element_returns_itself(self) -> None:
        jack = _jackknife_means(np.array([5.0]))
        self.assertEqual(len(jack), 1)
        self.assertAlmostEqual(jack[0], 5.0)


# ------------------------------------------------------------------------- bca_ci
class TestBcaCi(unittest.TestCase):
    def test_returns_two_floats(self) -> None:
        rng = np.random.default_rng(0)
        vals = rng.normal(1.0, 0.1, size=50)
        boot = bootstrap_distribution(vals, N_BOOT, SEED)
        lo, hi = bca_ci(vals, boot)
        self.assertIsInstance(lo, float)
        self.assertIsInstance(hi, float)
        self.assertLessEqual(lo, hi)

    def test_ci_brackets_point_estimate(self) -> None:
        rng = np.random.default_rng(0)
        vals = rng.normal(1.0, 0.1, size=100)
        boot = bootstrap_distribution(vals, N_BOOT, SEED)
        lo, hi = bca_ci(vals, boot)
        # point estimate should be inside the CI (with high probability)
        self.assertLessEqual(lo, vals.mean() + 1e-6)
        self.assertGreaterEqual(hi, vals.mean() - 1e-6)

    def test_constant_data_falls_back_to_percentile(self) -> None:
        # constant data -> acceleration undefined -> falls back to percentile.
        vals = np.array([2.5] * 10)
        boot = bootstrap_distribution(vals, N_BOOT, SEED)
        lo, hi = bca_ci(vals, boot)
        self.assertAlmostEqual(lo, 2.5)
        self.assertAlmostEqual(hi, 2.5)

    def test_deterministic_with_seed(self) -> None:
        rng = np.random.default_rng(0)
        vals = rng.normal(1.0, 0.1, size=50)
        boot1 = bootstrap_distribution(vals, N_BOOT, SEED)
        boot2 = bootstrap_distribution(vals, N_BOOT, SEED)
        lo1, hi1 = bca_ci(vals, boot1)
        lo2, hi2 = bca_ci(vals, boot2)
        self.assertAlmostEqual(lo1, lo2)
        self.assertAlmostEqual(hi1, hi2)


# ----------------------------------------------------- paired_delta_distribution
class TestPairedDeltaDistribution(unittest.TestCase):
    def test_shape(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0])
        b = np.array([0.5, 1.5, 2.5, 3.5])
        dist = paired_delta_distribution(a, b, 100, 42)
        self.assertEqual(len(dist), 100)

    def test_constant_delta(self) -> None:
        # a - b is constant 0.5 -> every bootstrap mean delta is 0.5
        a = np.array([1.5, 2.5, 3.5, 4.5])
        b = np.array([1.0, 2.0, 3.0, 4.0])
        dist = paired_delta_distribution(a, b, 100, 42)
        self.assertTrue(np.allclose(dist, 0.5))

    def test_mismatched_shapes_raise(self) -> None:
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.0, 2.0])
        with self.assertRaises(ValueError):
            paired_delta_distribution(a, b, 10, 42)


# --------------------------------------------------------------- paired_delta_ci
class TestPairedDeltaCi(unittest.TestCase):
    def test_returns_two_floats(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        b = np.array([0.5, 1.5, 2.5, 3.5, 4.5])
        lo, hi = paired_delta_ci(a, b, 100, 42)
        self.assertIsInstance(lo, float)
        self.assertIsInstance(hi, float)
        self.assertLessEqual(lo, hi)

    def test_constant_positive_delta_ci_brackets_delta(self) -> None:
        a = np.array([1.5, 2.5, 3.5, 4.5])
        b = np.array([1.0, 2.0, 3.0, 4.0])
        lo, hi = paired_delta_ci(a, b, 100, 42)
        self.assertAlmostEqual(lo, 0.5)
        self.assertAlmostEqual(hi, 0.5)


# --------------------------------------------------------------- end-to-end run
class TestEndToEndRun(unittest.TestCase):
    def test_run_returns_summary_with_expected_keys(self) -> None:
        summary = run()
        for key in [
            "label", "rq", "n_windows", "n_tied", "n_nontied",
            "tied_window_ids", "nontied_window_ids", "tie_definition",
            "method", "thresholds", "bootstrap", "decision_counts",
            "rq39_reference", "all_windows", "nontied", "hypothesis_verdicts",
        ]:
            self.assertIn(key, summary)
        self.assertEqual(summary["label"], "experimental/frontier")
        self.assertEqual(summary["n_windows"], 77)

    def test_run_tie_and_nontied_counts(self) -> None:
        summary = run()
        self.assertEqual(summary["n_tied"], 35)
        self.assertEqual(summary["n_nontied"], 42)
        self.assertEqual(len(summary["tied_window_ids"]), 35)
        self.assertEqual(len(summary["nontied_window_ids"]), 42)
        # partition: tied + nontied = all 77 window_ids
        all_ids = set(summary["tied_window_ids"]) | set(summary["nontied_window_ids"])
        self.assertEqual(len(all_ids), 77)

    def test_run_all_windows_reproduces_rq39(self) -> None:
        # Sanity: the all-windows corrected cpWER must reproduce RQ39's
        # word-level point estimate (1.043290) and BCa CI [1.012987, 1.097403].
        summary = run()
        aw = summary["all_windows"]
        self.assertAlmostEqual(aw["corrected_router_cpwer"], 1.04329, places=5)
        self.assertAlmostEqual(aw["always_mixed_cpwer"], 1.17316, places=5)
        self.assertAlmostEqual(aw["oracle_best_cpwer"], 1.017316, places=5)
        self.assertAlmostEqual(aw["bca_ci_95"][0], 1.012987, places=5)
        self.assertAlmostEqual(aw["bca_ci_95"][1], 1.097403, places=5)
        self.assertAlmostEqual(
            aw["bca_ci_width"], RQ39_WORD_LEVEL_BCA_WIDTH, places=5
        )

    def test_run_nontied_corrected_cpwer(self) -> None:
        # On the 42 non-tied windows the corrected router's cpWER must be
        # HIGHER than on all-windows (the 35 tied windows were mostly at
        # cpWER=1.0, pulling the average down).
        summary = run()
        nt = summary["nontied"]
        aw = summary["all_windows"]
        self.assertEqual(nt["n"], 42)
        self.assertGreater(nt["corrected_router_cpwer"], aw["corrected_router_cpwer"])
        self.assertGreater(nt["always_mixed_cpwer"], aw["always_mixed_cpwer"])
        self.assertGreater(nt["oracle_best_cpwer"], aw["oracle_best_cpwer"])

    def test_run_nontied_bca_ci_width_widens(self) -> None:
        # Excluding tied windows removes the variance-reducing 1.0 anchors,
        # so the BCa CI WIDENS, not shrinks. H50b is killed.
        summary = run()
        nt = summary["nontied"]
        aw = summary["all_windows"]
        self.assertGreater(nt["bca_ci_width"], aw["bca_ci_width"])
        self.assertGreater(nt["bca_ci_width"], RQ39_WORD_LEVEL_BCA_WIDTH)

    def test_run_nontied_ci_still_includes_oracle(self) -> None:
        # H50a killed: BCa lower bound on non-tied is BELOW the non-tied
        # oracle cpWER.
        summary = run()
        nt = summary["nontied"]
        self.assertLessEqual(nt["bca_ci_95"][0], nt["oracle_best_cpwer"])

    def test_run_nontied_improvement_larger_than_all(self) -> None:
        # H50c supported: improvement (mixed - corrected) is larger on
        # non-tied windows than on all windows.
        summary = run()
        nt = summary["nontied"]
        aw = summary["all_windows"]
        self.assertGreater(
            nt["improvement_mixed_minus_corrected"],
            aw["improvement_mixed_minus_corrected"],
        )

    def test_run_hypothesis_verdicts(self) -> None:
        summary = run()
        h = summary["hypothesis_verdicts"]
        # H50a killed (CI includes oracle on non-tied)
        self.assertFalse(h["H50a"]["supported"])
        self.assertIn("supported", h["H50a"])
        # H50b killed (non-tied width >= RQ39 width)
        self.assertFalse(h["H50b"]["supported"])
        # H50c supported (non-tied improvement > all-windows improvement)
        self.assertTrue(h["H50c"]["supported"])

    def test_run_decision_counts(self) -> None:
        summary = run()
        dc = summary["decision_counts"]
        # All-windows: should match RQ39/RQ16 (mixed=38, separated=39)
        self.assertEqual(dc["all_windows"]["mixed"], 38)
        self.assertEqual(dc["all_windows"]["separated"], 39)
        # Non-tied: 42 windows total
        self.assertEqual(dc["nontied"]["mixed"] + dc["nontied"]["separated"], 42)

    def test_run_thresholds_recorded(self) -> None:
        summary = run()
        self.assertEqual(summary["thresholds"]["lang_id_entropy"], 0.38)
        self.assertEqual(summary["thresholds"]["tie_tolerance"], TIE_TOL)

    def test_run_bootstrap_config(self) -> None:
        summary = run()
        self.assertEqual(summary["bootstrap"]["n_boot"], N_BOOT)
        self.assertEqual(summary["bootstrap"]["seed"], SEED)
        self.assertEqual(summary["bootstrap"]["alpha"], ALPHA)

    def test_run_rq39_reference_recorded(self) -> None:
        summary = run()
        ref = summary["rq39_reference"]
        self.assertEqual(ref["word_level_bca_ci_95"], list(RQ39_WORD_LEVEL_BCA_CI))
        self.assertAlmostEqual(
            ref["word_level_bca_width"], RQ39_WORD_LEVEL_BCA_WIDTH
        )
        self.assertAlmostEqual(
            ref["word_level_corrected_router_cpwer"],
            RQ39_WORD_LEVEL_CORRECTED_CPWER,
        )
        self.assertAlmostEqual(
            ref["word_level_oracle_best_cpwer"], RQ39_WORD_LEVEL_ORACLE_CPWER
        )

    def test_run_writes_csv_with_77_rows(self) -> None:
        run()
        csv_path = SCRIPT_DIR / "tied_window_exclusion_results.csv"
        self.assertTrue(csv_path.exists())
        with open(csv_path, encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        # 1 header + 77 data rows
        self.assertEqual(len(lines), 78)

    def test_run_writes_json_with_per_window(self) -> None:
        summary = run()
        json_path = SCRIPT_DIR / "tied_window_exclusion_results.json"
        self.assertTrue(json_path.exists())
        with open(json_path, encoding="utf-8") as f:
            on_disk = json.load(f)
        self.assertIn("per_window", on_disk)
        self.assertEqual(len(on_disk["per_window"]), 77)
        # the summary dict returned by run() and the on-disk JSON must agree
        # on the headline numbers
        self.assertEqual(
            on_disk["n_tied"], summary["n_tied"]
        )
        self.assertEqual(
            on_disk["n_nontied"], summary["n_nontied"]
        )


if __name__ == "__main__":
    unittest.main()
