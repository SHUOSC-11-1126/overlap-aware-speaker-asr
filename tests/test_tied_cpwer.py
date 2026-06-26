"""Tests for RQ47 tied-cpWER window characterisation (experimental/frontier).

Pin the PURE helpers used by
``results/frontier/tied_cpwer_characterisation/tied_cpwer_analysis.py``:
``identify_tied_windows``, ``extract_window_features``, ``mann_whitney_u``,
``logistic_regression_loo_auc`` (plus the supporting lang-id / ranking / AUC
helpers they depend on). Synthetic data for the pure-helper tests; two smoke
tests load the real AISHELL-4 JSON (read-only) to pin the verified tie count.

Note on the tie count: the task brief's narrative mentions "5 tied windows",
but the stated operational definition
``abs(always_mixed_cpwer - always_separated_cpwer) < 1e-6`` yields **35** tied
windows on the 77-window AISHELL-4 file (34 of which tie at exactly 1.0). No
natural alternative definition yields 5. The smoke tests therefore assert the
verified count (35) under the precise operational definition; the discrepancy
is documented in FINDINGS.md and the PR body. Asserting 5 would make the smoke
test fail on the real data.
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
    / "tied_cpwer_characterisation"
)
sys.path.insert(0, str(SCRIPT_DIR))

from tied_cpwer_analysis import (  # noqa: E402
    CLASSIFIER_FEATURES,
    MWU_FEATURES,
    _auc_from_scores,
    _logistic_fit,
    _logistic_predict,
    _sigmoid,
    extract_window_features,
    identify_tied_windows,
    language_id_entropy,
    logistic_regression_loo_auc,
    mann_whitney_u,
    max_across_speakers,
    rankdata_average,
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
    num_speakers: int = 2,
    overlap_ratio: float = 0.0,
    overlap_level: int = 0,
    overlap_label: str = "NoOverlap",
    mixed_text_length: int = 10,
    separated_total_length: int = 10,
    runtime_ratio: float = 1.0,
    oracle_best_cpwer: float = 1.0,
    sep_texts: dict | None = None,
    ref_texts: dict | None = None,
    router_v2_method: str = "separated",
) -> dict:
    """Build a minimal synthetic window with the fields the analysis reads."""
    if sep_texts is None:
        sep_texts = {"s1": "你好", "s2": "世界"} if num_speakers >= 2 else {"s1": "你好"}
    if ref_texts is None:
        ref_texts = sep_texts
    return {
        "window_id": window_id,
        "always_mixed_cpwer": mixed_cpwer,
        "always_separated_cpwer": sep_cpwer,
        "num_speakers": num_speakers,
        "overlap_ratio": overlap_ratio,
        "overlap_level": overlap_level,
        "overlap_label": overlap_label,
        "mixed_text_length": mixed_text_length,
        "separated_total_length": separated_total_length,
        "runtime_ratio": runtime_ratio,
        "oracle_best_cpwer": oracle_best_cpwer,
        "router_v2_method": router_v2_method,
        "separated_text_per_speaker": sep_texts,
        "ref_text_per_speaker": ref_texts,
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
        self.assertEqual(script_category("z"), "Latin")

    def test_digit(self) -> None:
        self.assertEqual(script_category("7"), "Digit")

    def test_punct(self) -> None:
        self.assertEqual(script_category(","), "Punct")


# ----------------------------------------------------------- language_id_entropy
class TestLanguageIdEntropy(unittest.TestCase):
    def test_empty_is_zero(self) -> None:
        self.assertEqual(language_id_entropy(""), 0.0)
        self.assertEqual(language_id_entropy("   "), 0.0)

    def test_pure_han_is_zero_entropy(self) -> None:
        # A single script category -> Shannon entropy of 0 bits.
        self.assertAlmostEqual(language_id_entropy("你好世界你好"), 0.0, places=12)

    def test_mixed_scripts_higher_entropy(self) -> None:
        h_pure = language_id_entropy("你好你好")
        h_mixed = language_id_entropy("你好abc你好")
        self.assertGreater(h_mixed, h_pure)
        self.assertGreater(h_mixed, 0.0)

    def test_deterministic(self) -> None:
        text = "你好abc世界def"
        self.assertEqual(language_id_entropy(text), language_id_entropy(text))


# ------------------------------------------------------------ max_across_speakers
class TestMaxAcrossSpeakers(unittest.TestCase):
    def test_empty_dict_is_zero(self) -> None:
        self.assertEqual(max_across_speakers({}), 0.0)

    def test_max_of_multiple_speakers(self) -> None:
        # speaker 2 mixes scripts -> higher entropy than pure-Han speaker 1.
        texts = {"s1": "你好你好", "s2": "你好abc你好"}
        v = max_across_speakers(texts)
        self.assertEqual(v, language_id_entropy("你好abc你好"))

    def test_skips_empty_speakers(self) -> None:
        texts = {"s1": "", "s2": "   ", "s3": "你好abc"}
        v = max_across_speakers(texts)
        self.assertEqual(v, language_id_entropy("你好abc"))


# ---------------------------------------------------------- identify_tied_windows
class TestIdentifyTiedWindows(unittest.TestCase):
    def test_synthetic_clear_tie_and_nontie(self) -> None:
        ws = [
            _win(0, 1.0, 1.0),       # tied
            _win(1, 1.0, 2.0),       # not tied
            _win(2, 1.3333333, 1.3333334),  # tied within tol
        ]
        self.assertEqual(identify_tied_windows(ws), [0, 2])

    def test_tolerance_respected(self) -> None:
        ws = [_win(0, 1.0, 1.0 + 1e-5)]  # difference > tol -> not tied
        self.assertEqual(identify_tied_windows(ws, tol=1e-6), [])

    def test_tolerance_inclusive(self) -> None:
        ws = [_win(0, 1.0, 1.0 + 1e-9)]  # difference < tol -> tied
        self.assertEqual(identify_tied_windows(ws, tol=1e-6), [0])

    def test_returns_window_ids_not_indices(self) -> None:
        ws = [_win(10, 1.0, 1.0), _win(20, 1.0, 2.0)]
        self.assertEqual(identify_tied_windows(ws), [10])

    def test_smoke_aishell4_tied_count_is_35(self) -> None:
        # Smoke test on the real AISHELL-4 data. The stated operational
        # definition yields 35 tied windows (34 at exactly 1.0). The brief's
        # "5" is inconsistent with this definition; see module docstring.
        with open(SOURCE_JSON, encoding="utf-8") as f:
            data = json.load(f)
        tied = identify_tied_windows(data["windows"])
        self.assertEqual(len(tied), 35)
        self.assertEqual(len(data["windows"]), 77)

    def test_smoke_aishell4_known_tied_and_nontied(self) -> None:
        with open(SOURCE_JSON, encoding="utf-8") as f:
            data = json.load(f)
        tied = set(identify_tied_windows(data["windows"]))
        # window 0: mixed=1.0, sep=2.333 -> NOT tied
        self.assertNotIn(0, tied)
        # window 3: mixed=1.0, sep=1.0 -> tied
        self.assertIn(3, tied)

    def test_smoke_aishell4_tied_at_one_count(self) -> None:
        with open(SOURCE_JSON, encoding="utf-8") as f:
            data = json.load(f)
        tied_at_one = [
            w["window_id"]
            for w in data["windows"]
            if abs(w["always_mixed_cpwer"] - w["always_separated_cpwer"]) < 1e-6
            and w["always_mixed_cpwer"] == 1.0
        ]
        self.assertEqual(len(tied_at_one), 34)


# ----------------------------------------------------------- extract_window_features
class TestExtractWindowFeatures(unittest.TestCase):
    def test_returns_all_expected_keys(self) -> None:
        feats = extract_window_features(_win(0, 1.0, 1.0))
        for key in [
            "window_id", "speaker_count", "active_speaker_count",
            "active_speaker_count_ref", "overlap_ratio", "mixed_text_length",
            "separated_text_length", "total_separated_chars", "runtime_ratio",
            "avg_speaker_length_sep", "lang_id_entropy", "compression_ratio",
            "always_mixed_cpwer", "always_separated_cpwer",
        ]:
            self.assertIn(key, feats)

    def test_speaker_count_from_num_speakers(self) -> None:
        feats = extract_window_features(_win(0, 1.0, 1.0, num_speakers=3))
        self.assertEqual(feats["speaker_count"], 3)

    def test_active_speaker_count_counts_nonempty_sep(self) -> None:
        sep = {"s1": "你好", "s2": "", "s3": "   "}
        feats = extract_window_features(_win(0, 1.0, 1.0, num_speakers=3, sep_texts=sep))
        self.assertEqual(feats["active_speaker_count"], 1)

    def test_active_speaker_count_ref_uses_references(self) -> None:
        sep = {"s1": "", "s2": ""}
        ref = {"s1": "你好", "s2": "世界", "s3": ""}
        feats = extract_window_features(_win(0, 1.0, 1.0, num_speakers=3, sep_texts=sep, ref_texts=ref))
        self.assertEqual(feats["active_speaker_count"], 0)
        self.assertEqual(feats["active_speaker_count_ref"], 2)

    def test_silence_window_features_are_zero(self) -> None:
        # Empty mixed and separated -> lengths/entropy/compression collapse to 0.
        w = _win(
            0, 1.0, 1.0, num_speakers=1, mixed_text_length=0,
            separated_total_length=0, sep_texts={"s1": ""}, ref_texts={"s1": "你好"},
        )
        feats = extract_window_features(w)
        self.assertEqual(feats["mixed_text_length"], 0)
        self.assertEqual(feats["separated_text_length"], 0)
        self.assertEqual(feats["active_speaker_count"], 0)
        self.assertEqual(feats["avg_speaker_length_sep"], 0.0)
        self.assertEqual(feats["lang_id_entropy"], 0.0)
        self.assertEqual(feats["compression_ratio"], 0.0)

    def test_compression_ratio_floors_mixed_at_one(self) -> None:
        # mixed_text_length=0 -> denominator floored to 1, ratio = sep/1.
        w = _win(0, 1.0, 1.0, separated_total_length=50, mixed_text_length=0,
                 sep_texts={"s1": "x" * 50})
        feats = extract_window_features(w)
        self.assertEqual(feats["compression_ratio"], 50.0)

    def test_total_separated_chars_equals_sum_of_lengths(self) -> None:
        sep = {"s1": "你好", "s2": "世界abc"}
        w = _win(0, 1.0, 1.0, num_speakers=2, sep_texts=sep)
        feats = extract_window_features(w)
        self.assertEqual(feats["total_separated_chars"], 2 + 5)

    def test_avg_speaker_length_sep_uses_active_count(self) -> None:
        # separated_total_length=60, two speakers but only one active -> 60/1.
        sep = {"s1": "x" * 60, "s2": ""}
        w = _win(0, 1.0, 1.0, num_speakers=2, separated_total_length=60, sep_texts=sep)
        feats = extract_window_features(w)
        self.assertAlmostEqual(feats["avg_speaker_length_sep"], 60.0)

    def test_lang_id_entropy_from_separated_texts(self) -> None:
        sep = {"s1": "你好abc"}  # Han + Latin -> positive entropy
        w = _win(0, 1.0, 1.0, num_speakers=1, sep_texts=sep)
        feats = extract_window_features(w)
        self.assertGreater(feats["lang_id_entropy"], 0.0)
        self.assertAlmostEqual(feats["lang_id_entropy"], language_id_entropy("你好abc"))


# ------------------------------------------------------------------ rankdata_average
class TestRankdataAverage(unittest.TestCase):
    def test_no_ties_are_1_based_order(self) -> None:
        r = rankdata_average([30.0, 10.0, 20.0])
        # 10->1, 20->2, 30->3
        np.testing.assert_allclose(r, [3.0, 1.0, 2.0])

    def test_ties_share_midrank(self) -> None:
        r = rankdata_average([1.0, 1.0, 2.0])
        # the two 1.0s share ranks (1+2)/2 = 1.5; the 2.0 gets rank 3
        np.testing.assert_allclose(r, [1.5, 1.5, 3.0])

    def test_all_equal(self) -> None:
        r = rankdata_average([5.0, 5.0, 5.0, 5.0])
        # all share (1+2+3+4)/4 = 2.5
        np.testing.assert_allclose(r, [2.5, 2.5, 2.5, 2.5])


# ----------------------------------------------------------------- mann_whitney_u
class TestMannWhitneyU(unittest.TestCase):
    def test_x_all_smaller_than_y(self) -> None:
        # x=[1..5], y=[6..10]: U_x=0, rank-biserial=-1, small p (n=5 each is
        # enough for the normal-approx p to clear 0.05 under complete separation).
        res = mann_whitney_u([1, 2, 3, 4, 5], [6, 7, 8, 9, 10])
        self.assertAlmostEqual(res["U"], 0.0)
        self.assertAlmostEqual(res["rank_biserial"], -1.0)
        self.assertLess(res["p_two_sided"], 0.05)

    def test_x_all_larger_than_y(self) -> None:
        res = mann_whitney_u([6, 7, 8, 9, 10], [1, 2, 3, 4, 5])
        self.assertAlmostEqual(res["U"], 25.0)  # n1*n2
        self.assertAlmostEqual(res["rank_biserial"], 1.0)
        self.assertLess(res["p_two_sided"], 0.05)

    def test_identical_distributions_large_p_zero_effect(self) -> None:
        res = mann_whitney_u([1, 2, 3], [1, 2, 3])
        self.assertGreater(res["p_two_sided"], 0.5)
        self.assertAlmostEqual(res["rank_biserial"], 0.0, places=9)

    def test_effect_size_sign_flips_when_x_smaller(self) -> None:
        smaller = mann_whitney_u([1, 2, 3], [10, 11, 12])["rank_biserial"]
        larger = mann_whitney_u([10, 11, 12], [1, 2, 3])["rank_biserial"]
        self.assertLess(smaller, 0.0)
        self.assertGreater(larger, 0.0)
        self.assertAlmostEqual(smaller, -larger, places=9)

    def test_two_sided_p_symmetric_under_swap(self) -> None:
        a = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        b = [1.5, 2.5, 3.5, 4.5, 5.5, 7.0]
        p_ab = mann_whitney_u(a, b)["p_two_sided"]
        p_ba = mann_whitney_u(b, a)["p_two_sided"]
        self.assertAlmostEqual(p_ab, p_ba, places=9)

    def test_empty_group_returns_nan(self) -> None:
        res = mann_whitney_u([], [1, 2, 3])
        self.assertTrue(math.isnan(res["U"]))
        self.assertTrue(math.isnan(res["p_two_sided"]))


# ----------------------------------------------------------------- _auc_from_scores
class TestAucFromScores(unittest.TestCase):
    def test_perfect_separation_auc_one(self) -> None:
        scores = [0.1, 0.2, 0.9, 1.0]
        labels = [0, 0, 1, 1]
        self.assertAlmostEqual(_auc_from_scores(scores, labels), 1.0)

    def test_perfect_inverse_auc_zero(self) -> None:
        scores = [0.9, 1.0, 0.1, 0.2]
        labels = [0, 0, 1, 1]
        self.assertAlmostEqual(_auc_from_scores(scores, labels), 0.0)

    def test_tied_scores_auc_half(self) -> None:
        scores = [0.5, 0.5, 0.5, 0.5]
        labels = [0, 0, 1, 1]
        self.assertAlmostEqual(_auc_from_scores(scores, labels), 0.5)

    def test_empty_class_returns_half(self) -> None:
        self.assertAlmostEqual(_auc_from_scores([0.1, 0.2, 0.3], [0, 0, 0]), 0.5)
        self.assertAlmostEqual(_auc_from_scores([0.1, 0.2, 0.3], [1, 1, 1]), 0.5)

    def test_known_partial_overlap(self) -> None:
        # positives scores [0.6, 0.8], negatives [0.2, 0.6]
        # pairs (pos, neg): (0.6 vs 0.2)->win, (0.6 vs 0.6)->tie(0.5),
        # (0.8 vs 0.2)->win, (0.8 vs 0.6)->win  => 3.5 / 4 = 0.875
        scores = [0.6, 0.8, 0.2, 0.6]
        labels = [1, 1, 0, 0]
        self.assertAlmostEqual(_auc_from_scores(scores, labels), 0.875)


# ------------------------------------------------------------- logistic regression
class TestLogisticRegressionHelpers(unittest.TestCase):
    def test_sigmoid_in_unit_interval(self) -> None:
        s = _sigmoid(np.array([-10.0, -1.0, 0.0, 1.0, 10.0]))
        self.assertTrue(np.all(s > 0.0) and np.all(s < 1.0))
        self.assertAlmostEqual(float(_sigmoid(np.array([0.0]))[0]), 0.5)

    def test_fit_returns_bias_plus_feature_weights(self) -> None:
        X = np.array([[0.0], [1.0], [2.0], [3.0]])
        y = np.array([0, 0, 1, 1])
        w, mu, sd = _logistic_fit(X, y, seed=42)
        self.assertEqual(w.shape[0], 2)  # 1 feature + bias

    def test_predict_shape_matches_input(self) -> None:
        X = np.array([[0.0], [1.0], [2.0], [3.0]])
        y = np.array([0, 0, 1, 1])
        w, mu, sd = _logistic_fit(X, y, seed=42)
        p = _logistic_predict(w, mu, sd, X)
        self.assertEqual(p.shape, (4,))

    def test_fit_separable_data_orders_predictions(self) -> None:
        # class 1 has high feature value, class 0 low -> predictions rank correctly.
        X = np.array([[-5.0], [-4.0], [4.0], [5.0]])
        y = np.array([0, 0, 1, 1])
        w, mu, sd = _logistic_fit(X, y, seed=42)
        p = _logistic_predict(w, mu, sd, X)
        # both positives should score above both negatives
        self.assertGreater(float(p[2]), float(p[1]))
        self.assertGreater(float(p[3]), float(p[0]))


class TestLogisticRegressionLooAuc(unittest.TestCase):
    def test_perfectly_separable_auc_near_one(self) -> None:
        X = np.array([[-5.0], [-4.0], [-3.0], [3.0], [4.0], [5.0]])
        y = np.array([0, 0, 0, 1, 1, 1])
        res = logistic_regression_loo_auc(X, y, seed=42)
        self.assertGreaterEqual(res["auc"], 0.95)

    def test_random_labels_auc_not_systematically_perfect(self) -> None:
        # Non-informative features + random labels: the LOO AUC must not be
        # systematically near 0 or 1 (it wanders around 0.5 on noise).
        rng = np.random.default_rng(0)
        X = rng.normal(0, 1, size=(40, 3))
        y = rng.integers(0, 2, size=40)
        res = logistic_regression_loo_auc(X, y, seed=42, n_iter=500)
        self.assertGreater(res["auc"], 0.15)
        self.assertLess(res["auc"], 0.85)

    def test_returns_expected_keys(self) -> None:
        X = np.array([[0.0], [1.0], [2.0], [3.0]])
        y = np.array([0, 0, 1, 1])
        res = logistic_regression_loo_auc(X, y, seed=42, n_iter=200)
        for key in ["auc", "n", "n_pos", "n_neg", "seed", "oof_scores",
                    "coeffs_standardised", "feature_means", "feature_stds"]:
            self.assertIn(key, res)

    def test_oof_length_equals_n(self) -> None:
        X = np.array([[0.0], [1.0], [2.0], [3.0], [4.0]])
        y = np.array([0, 0, 1, 1, 1])
        res = logistic_regression_loo_auc(X, y, seed=42, n_iter=200)
        self.assertEqual(len(res["oof_scores"]), 5)
        self.assertEqual(res["n"], 5)

    def test_deterministic_with_seed(self) -> None:
        X = np.array([[0.0], [1.0], [2.0], [3.0], [4.0], [5.0]])
        y = np.array([0, 0, 0, 1, 1, 1])
        a = logistic_regression_loo_auc(X, y, seed=42, n_iter=300)
        b = logistic_regression_loo_auc(X, y, seed=42, n_iter=300)
        self.assertAlmostEqual(a["auc"], b["auc"])

    def test_smoke_aishell4_auc_above_threshold(self) -> None:
        # H47c smoke: the metadata-only LOO-CV AUC on AISHELL-4 must clear 0.70.
        from tied_cpwer_analysis import build_feature_matrix
        with open(SOURCE_JSON, encoding="utf-8") as f:
            data = json.load(f)
        X, y, _ = build_feature_matrix(data["windows"], CLASSIFIER_FEATURES)
        res = logistic_regression_loo_auc(X, y, seed=42)
        self.assertGreater(res["auc"], 0.70)
        self.assertEqual(res["n"], 77)


# ------------------------------------------------------------------- end-to-end
class TestEndToEndRun(unittest.TestCase):
    def test_run_returns_summary_with_expected_keys(self) -> None:
        summary = run()
        for key in [
            "label", "rq", "n_windows", "n_tied", "n_non_tied",
            "tied_window_ids", "mann_whitney", "logistic_regression",
            "hypotheses", "qualitative", "seed",
        ]:
            self.assertIn(key, summary)
        self.assertEqual(summary["label"], "experimental/frontier")
        self.assertEqual(summary["n_windows"], 77)

    def test_run_hypothesis_verdicts_consistent(self) -> None:
        summary = run()
        h = summary["hypotheses"]
        # H47a supported (fewer active speakers, p<0.05, negative effect)
        self.assertTrue(h["H47a"]["supported"])
        self.assertLess(h["H47a"]["p_two_sided"], 0.05)
        self.assertLess(h["H47a"]["rank_biserial"], 0.0)
        # H47b killed (overlap ratio not significant at 0.05)
        self.assertFalse(h["H47b"]["supported"])
        # H47c supported (AUC > 0.70)
        self.assertTrue(h["H47c"]["supported"])
        self.assertGreater(h["H47c"]["auc"], 0.70)

    def test_run_writes_csv_with_77_rows(self) -> None:
        run()
        csv_path = SCRIPT_DIR / "tied_cpwer_results.csv"
        self.assertTrue(csv_path.exists())
        with open(csv_path, encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        # 1 header + 77 data rows
        self.assertEqual(len(lines), 78)

    def test_run_mwu_covers_all_mwu_features(self) -> None:
        summary = run()
        for feat in MWU_FEATURES:
            self.assertIn(feat, summary["mann_whitney"])
            for key in ["U", "p_two_sided", "rank_biserial", "n1", "n2"]:
                self.assertIn(key, summary["mann_whitney"][feat])


if __name__ == "__main__":
    unittest.main()
