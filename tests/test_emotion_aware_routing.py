"""Tests for RQ53 emotion-aware routing simulation (experimental/frontier).

Pin the PURE helpers in
``results/frontier/emotion_aware_routing/emotion_aware_routing_analysis.py``:
transcript concatenation/hashing, emotion-signal extraction (incl. fail-open for
silent windows), text-signal extraction, the four routing policies, per-window /
mean cpWER computation, the disagreement cross-tab, bootstrap CI, and the
pre-registered hypothesis verdicts (H53a/H53b/H53c kill conditions). Synthetic
data for the pure-helper tests; four smoke tests load the real AISHELL-4 + RQ36 +
RQ16 artefacts (read-only) to pin the verified aggregate numbers (77 windows,
text-only cpWER == RQ16's 1.04329, disagreement > 20%, coverage of 67/77 emotion
readings).
"""
from __future__ import annotations

import json
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
    / "emotion_aware_routing"
)
sys.path.insert(0, str(SCRIPT_DIR))

from emotion_aware_routing_analysis import (  # noqa: E402
    DISAGREEMENT_THRESHOLD,
    EMOTION_FAILOPEN_RELIABLE,
    ROUTE_MIXED,
    ROUTE_SEPARATED,
    TEXT_BASELINE_CPWER,
    bootstrap_cpwer_ci,
    compute_disagreement,
    compute_policy_cpwer,
    concat_separated,
    evaluate_hypotheses,
    extract_emotion_signal,
    extract_text_signal,
    load_aishell4_windows,
    load_emotion_cache,
    load_rq16_per_window,
    policy_and,
    policy_emotion_only,
    policy_or,
    policy_text_only,
    route_cpwer,
    simulate,
    transcript_hash,
)

AISHELL4_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
EMOTION_CACHE_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "llm_emotion_hallucination"
    / "llm_responses_cache.json"
)
RQ16_SIM_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "corrected_router_simulation"
    / "simulation_results.json"
)


# ----------------------------------------------------------------- fixtures
def _window(
    window_id: int,
    sep_texts: dict | None = None,
    mixed_text: str = "",
    mixed_cpwer: float = 1.0,
    sep_cpwer: float = 1.0,
    overlap_label: str = "NoOverlap",
) -> dict:
    """Build a minimal AISHELL-4-style window dict."""
    return {
        "window_id": window_id,
        "separated_text_per_speaker": sep_texts or {},
        "mixed_text": mixed_text,
        "always_mixed_cpwer": mixed_cpwer,
        "always_separated_cpwer": sep_cpwer,
        "overlap_label": overlap_label,
    }


def _rq16_row(window_id: int, decision: str) -> dict:
    return {"window_id": window_id, "corrected_decision": decision}


# =========================================================================
class TestConcatSeparated(unittest.TestCase):
    """concat_separated: per-speaker concatenation + mixed-text fallback."""

    def test_concatenates_non_empty_speakers(self):
        w = _window(0, sep_texts={"001-M": "你好", "002-M": "世界"})
        self.assertEqual(concat_separated(w), "你好世界")

    def test_skips_empty_and_whitespace_speakers(self):
        w = _window(0, sep_texts={"001-M": "你好", "002-M": "   ", "003-F": ""})
        self.assertEqual(concat_separated(w), "你好")

    def test_falls_back_to_mixed_when_separated_empty(self):
        w = _window(0, sep_texts={}, mixed_text="混合文本")
        self.assertEqual(concat_separated(w), "混合文本")

    def test_falls_back_to_mixed_when_separated_whitespace_only(self):
        w = _window(0, sep_texts={"001-M": "  "}, mixed_text="混合")
        self.assertEqual(concat_separated(w), "混合")

    def test_returns_empty_when_both_empty(self):
        w = _window(0, sep_texts={}, mixed_text="")
        self.assertEqual(concat_separated(w), "")

    def test_ignores_none_values(self):
        w = _window(0, sep_texts={"001-M": None, "002-M": "ok"})
        self.assertEqual(concat_separated(w), "ok")


# =========================================================================
class TestTranscriptHash(unittest.TestCase):
    """transcript_hash: sha1 first 16 hex, matches RQ36's hashing."""

    def test_returns_16_hex_chars(self):
        h = transcript_hash("some transcript")
        self.assertEqual(len(h), 16)
        self.assertRegex(h, r"^[0-9a-f]{16}$")

    def test_deterministic(self):
        self.assertEqual(transcript_hash("abc"), transcript_hash("abc"))

    def test_different_inputs_different_hashes(self):
        self.assertNotEqual(transcript_hash("abc"), transcript_hash("abd"))

    def test_matches_rq36_helper(self):
        # Cross-check against the canonical RQ36 helper in src/.
        try:
            from src.llm_emotion_hallucination import transcript_hash as rq36_hash
        except ImportError:
            self.skipTest("src.llm_emotion_hallucination not importable")
        self.assertEqual(transcript_hash("你好世界"), rq36_hash("你好世界"))


# =========================================================================
class TestExtractEmotionSignal(unittest.TestCase):
    """extract_emotion_signal: cache lookup + fail-open for missing/silent."""

    def test_returns_reliable_true_on_cache_hit(self):
        w = _window(0, sep_texts={"001-M": "clean text"})
        cache = {transcript_hash("clean text"): {"reliable": True}}
        reliable, has_reading = extract_emotion_signal(w, cache)
        self.assertTrue(reliable)
        self.assertTrue(has_reading)

    def test_returns_reliable_false_on_cache_hit(self):
        w = _window(0, sep_texts={"001-M": "garbled"})
        cache = {transcript_hash("garbled"): {"reliable": False}}
        reliable, has_reading = extract_emotion_signal(w, cache)
        self.assertFalse(reliable)
        self.assertTrue(has_reading)

    def test_failopen_true_when_no_cache_entry(self):
        w = _window(0, sep_texts={"001-M": "uncached text"})
        reliable, has_reading = extract_emotion_signal(w, cache={})
        self.assertEqual(reliable, EMOTION_FAILOPEN_RELIABLE)
        self.assertFalse(has_reading)

    def test_failopen_true_for_silent_window(self):
        w = _window(0, sep_texts={}, mixed_text="")
        reliable, has_reading = extract_emotion_signal(w, cache={})
        self.assertEqual(reliable, EMOTION_FAILOPEN_RELIABLE)
        self.assertFalse(has_reading)

    def test_uses_mixed_text_fallback_for_silent_separated(self):
        # If separated is empty but mixed is present, hash the mixed text.
        w = _window(0, sep_texts={}, mixed_text="mixed fallback")
        cache = {transcript_hash("mixed fallback"): {"reliable": False}}
        reliable, has_reading = extract_emotion_signal(w, cache)
        self.assertFalse(reliable)
        self.assertTrue(has_reading)

    def test_cache_entry_without_reliable_field_is_failopen(self):
        w = _window(0, sep_texts={"001-M": "text"})
        cache = {transcript_hash("text"): {"emotion": "neutral"}}  # no reliable
        reliable, has_reading = extract_emotion_signal(w, cache)
        self.assertEqual(reliable, EMOTION_FAILOPEN_RELIABLE)
        self.assertFalse(has_reading)


# =========================================================================
class TestExtractTextSignal(unittest.TestCase):
    """extract_text_signal: text says unreliable iff RQ16 decision is mixed."""

    def test_mixed_decision_is_unreliable(self):
        self.assertTrue(extract_text_signal(_rq16_row(0, "mixed")))

    def test_separated_decision_is_reliable(self):
        self.assertFalse(extract_text_signal(_rq16_row(0, "separated")))

    def test_missing_decision_is_reliable(self):
        self.assertFalse(extract_text_signal({"window_id": 0}))

    def test_unknown_decision_is_reliable(self):
        self.assertFalse(extract_text_signal(_rq16_row(0, "unknown")))


# =========================================================================
class TestPolicies(unittest.TestCase):
    """The four routing policies."""

    def test_text_only_routes_mixed_when_text_unreliable(self):
        self.assertEqual(policy_text_only(True), ROUTE_MIXED)

    def test_text_only_routes_separated_when_text_reliable(self):
        self.assertEqual(policy_text_only(False), ROUTE_SEPARATED)

    def test_emotion_only_routes_mixed_when_emotion_unreliable(self):
        self.assertEqual(policy_emotion_only(True), ROUTE_MIXED)

    def test_emotion_only_routes_separated_when_emotion_reliable(self):
        self.assertEqual(policy_emotion_only(False), ROUTE_SEPARATED)

    def test_and_routes_mixed_if_either_unreliable(self):
        self.assertEqual(policy_and(True, True), ROUTE_MIXED)
        self.assertEqual(policy_and(True, False), ROUTE_MIXED)
        self.assertEqual(policy_and(False, True), ROUTE_MIXED)

    def test_and_routes_separated_only_when_both_reliable(self):
        self.assertEqual(policy_and(False, False), ROUTE_SEPARATED)

    def test_or_routes_mixed_only_when_both_unreliable(self):
        self.assertEqual(policy_or(True, True), ROUTE_MIXED)

    def test_or_routes_separated_if_either_reliable(self):
        self.assertEqual(policy_or(True, False), ROUTE_SEPARATED)
        self.assertEqual(policy_or(False, True), ROUTE_SEPARATED)
        self.assertEqual(policy_or(False, False), ROUTE_SEPARATED)

    def test_and_is_more_conservative_than_text_only(self):
        # AND routes mixed whenever text-only would, plus when emotion alone fires.
        for t in (True, False):
            for e in (True, False):
                if t:
                    self.assertEqual(policy_and(t, e), ROUTE_MIXED)
                # AND is mixed on a strict superset of text-only's mixed cases.

    def test_or_is_more_aggressive_than_text_only(self):
        # OR routes mixed only on a strict subset of text-only's mixed cases.
        for t in (True, False):
            for e in (True, False):
                if policy_or(t, e) == ROUTE_MIXED:
                    self.assertEqual(policy_text_only(t), ROUTE_MIXED)


# =========================================================================
class TestRouteCpwer(unittest.TestCase):
    """route_cpwer: pick the chosen route's stored cpWER."""

    def test_mixed_returns_mixed_cpwer(self):
        self.assertEqual(route_cpwer("mixed", 1.5, 2.0), 1.5)

    def test_separated_returns_separated_cpwer(self):
        self.assertEqual(route_cpwer("separated", 1.5, 2.0), 2.0)

    def test_unknown_decision_defaults_to_separated(self):
        self.assertEqual(route_cpwer("nonsense", 1.5, 2.0), 2.0)

    def test_returns_float(self):
        self.assertIsInstance(route_cpwer("mixed", 1, 2), float)


# =========================================================================
class TestComputePolicyCpwer(unittest.TestCase):
    """compute_policy_cpwer: mean cpWER over windows."""

    def test_mean_of_chosen_routes(self):
        windows = [
            _window(0, mixed_cpwer=1.0, sep_cpwer=2.0),
            _window(1, mixed_cpwer=2.0, sep_cpwer=1.0),
            _window(2, mixed_cpwer=1.0, sep_cpwer=1.0),
        ]
        decisions = ["mixed", "separated", "separated"]
        # (1.0 + 1.0 + 1.0) / 3
        self.assertAlmostEqual(compute_policy_cpwer(decisions, windows), 1.0)

    def test_all_mixed(self):
        windows = [_window(0, mixed_cpwer=2.0), _window(1, mixed_cpwer=4.0)]
        self.assertAlmostEqual(compute_policy_cpwer(["mixed", "mixed"], windows), 3.0)

    def test_all_separated(self):
        windows = [_window(0, sep_cpwer=2.0), _window(1, sep_cpwer=4.0)]
        self.assertAlmostEqual(
            compute_policy_cpwer(["separated", "separated"], windows), 3.0)

    def test_empty_returns_nan(self):
        self.assertTrue(np.isnan(compute_policy_cpwer([], [])))

    def test_length_mismatch_uses_zip(self):
        # zip stops at the shorter list; here 2 windows but 3 decisions.
        windows = [_window(0, mixed_cpwer=1.0), _window(1, mixed_cpwer=1.0)]
        decisions = ["mixed", "mixed", "mixed"]
        self.assertAlmostEqual(compute_policy_cpwer(decisions, windows), 1.0)


# =========================================================================
class TestComputeDisagreement(unittest.TestCase):
    """compute_disagreement: cross-tab + fraction where signals differ."""

    def test_no_disagreement_when_identical(self):
        d = compute_disagreement([True, False, True], [True, False, True])
        self.assertEqual(d["disagree_count"], 0)
        self.assertEqual(d["disagree_fraction"], 0.0)
        self.assertEqual(d["both_unreliable"], 2)
        self.assertEqual(d["both_reliable"], 1)

    def test_full_disagreement_when_opposite(self):
        d = compute_disagreement([True, False], [False, True])
        self.assertEqual(d["disagree_count"], 2)
        self.assertEqual(d["disagree_fraction"], 1.0)
        self.assertEqual(d["text_only_unreliable"], 1)
        self.assertEqual(d["emotion_only_unreliable"], 1)

    def test_mixed_signals(self):
        # T,T | T,F | F,T | F,F
        d = compute_disagreement([True, True, False, False], [True, False, True, False])
        self.assertEqual(d["n"], 4)
        self.assertEqual(d["disagree_count"], 2)
        self.assertAlmostEqual(d["disagree_fraction"], 0.5)
        self.assertEqual(d["both_unreliable"], 1)
        self.assertEqual(d["both_reliable"], 1)
        self.assertEqual(d["text_only_unreliable"], 1)
        self.assertEqual(d["emotion_only_unreliable"], 1)

    def test_empty_input(self):
        d = compute_disagreement([], [])
        self.assertEqual(d["n"], 0)
        self.assertEqual(d["disagree_fraction"], 0.0)

    def test_fraction_is_count_over_n(self):
        d = compute_disagreement([True] * 5, [False] * 5)
        self.assertEqual(d["disagree_count"], 5)
        self.assertAlmostEqual(d["disagree_fraction"], 1.0)


# =========================================================================
class TestBootstrapCpwerCi(unittest.TestCase):
    """bootstrap_cpwer_ci: mean + percentile CI, deterministic with seed."""

    def test_mean_equals_sample_mean(self):
        vals = [1.0, 2.0, 3.0, 4.0]
        ci = bootstrap_cpwer_ci(vals, n_boot=1000, seed=42)
        self.assertAlmostEqual(ci["mean"], 2.5)

    def test_ci_brackets_mean(self):
        ci = bootstrap_cpwer_ci([1.0, 2.0, 3.0, 4.0], n_boot=1000, seed=42)
        self.assertLessEqual(ci["ci_low"], ci["mean"])
        self.assertGreaterEqual(ci["ci_high"], ci["mean"])

    def test_deterministic_with_seed(self):
        vals = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        a = bootstrap_cpwer_ci(vals, n_boot=500, seed=7)
        b = bootstrap_cpwer_ci(vals, n_boot=500, seed=7)
        self.assertEqual(a, b)

    def test_empty_returns_nan(self):
        ci = bootstrap_cpwer_ci([])
        self.assertTrue(np.isnan(ci["mean"]))
        self.assertTrue(np.isnan(ci["ci_low"]))

    def test_constant_input_has_zero_width_ci(self):
        ci = bootstrap_cpwer_ci([1.5, 1.5, 1.5], n_boot=100, seed=1)
        self.assertAlmostEqual(ci["ci_low"], 1.5)
        self.assertAlmostEqual(ci["ci_high"], 1.5)


# =========================================================================
class TestEvaluateHypotheses(unittest.TestCase):
    """evaluate_hypotheses: H53a/H53b/H53c kill conditions."""

    def test_h53a_supported_when_and_le_baseline(self):
        v = evaluate_hypotheses(1.043, 1.1, 1.043, 1.05, 0.4)
        self.assertTrue(v["h53a"]["supported"])

    def test_h53a_killed_when_and_above_baseline(self):
        v = evaluate_hypotheses(1.043, 1.1, 1.10, 1.05, 0.4)
        self.assertFalse(v["h53a"]["supported"])

    def test_h53a_supported_at_equality(self):
        v = evaluate_hypotheses(1.043, 1.1, 1.043, 1.05, 0.4)
        self.assertTrue(v["h53a"]["supported"])

    def test_h53b_supported_when_or_below_baseline(self):
        v = evaluate_hypotheses(1.043, 1.1, 1.05, 1.02, 0.4)
        self.assertTrue(v["h53b"]["supported"])

    def test_h53b_killed_when_or_equals_baseline(self):
        # OR cpWER == baseline (exact) -> KILLED (success requires strictly <).
        v = evaluate_hypotheses(1.043, 1.1, 1.05, TEXT_BASELINE_CPWER, 0.4)
        self.assertFalse(v["h53b"]["supported"])

    def test_h53b_killed_when_or_above_baseline(self):
        v = evaluate_hypotheses(1.043, 1.1, 1.05, 1.05, 0.4)
        self.assertFalse(v["h53b"]["supported"])

    def test_h53c_supported_when_disagreement_above_threshold(self):
        v = evaluate_hypotheses(1.043, 1.1, 1.05, 1.05, 0.21)
        self.assertTrue(v["h53c"]["supported"])

    def test_h53c_killed_at_threshold(self):
        v = evaluate_hypotheses(1.043, 1.1, 1.05, 1.05, 0.20)
        self.assertFalse(v["h53c"]["supported"])

    def test_h53c_killed_below_threshold(self):
        v = evaluate_hypotheses(1.043, 1.1, 1.05, 1.05, 0.10)
        self.assertFalse(v["h53c"]["supported"])

    def test_threshold_is_20_percent(self):
        self.assertEqual(DISAGREEMENT_THRESHOLD, 0.20)

    def test_baseline_is_rq16_value(self):
        self.assertAlmostEqual(TEXT_BASELINE_CPWER, 1.04329)


# =========================================================================
class TestSimulateSynthetic(unittest.TestCase):
    """simulate: end-to-end on a small synthetic dataset."""

    def _setup(self):
        # 3 windows:
        #   w0: text unreliable (mixed), emotion unreliable (reliable=False) -> both T
        #   w1: text unreliable (mixed), emotion reliable   (reliable=True)  -> T,F (disagree)
        #   w2: text reliable   (separated), emotion reliable (reliable=True) -> F,F
        windows = [
            _window(0, sep_texts={"s": "garbled0"}, mixed_cpwer=1.0, sep_cpwer=2.0),
            _window(1, sep_texts={"s": "garbled1"}, mixed_cpwer=1.0, sep_cpwer=3.0),
            _window(2, sep_texts={"s": "clean2"}, mixed_cpwer=2.0, sep_cpwer=1.0),
        ]
        cache = {
            transcript_hash("garbled0"): {"reliable": False},
            transcript_hash("garbled1"): {"reliable": True},
            transcript_hash("clean2"): {"reliable": True},
        }
        rq16 = {
            0: _rq16_row(0, "mixed"),    # text unreliable
            1: _rq16_row(1, "mixed"),    # text unreliable
            2: _rq16_row(2, "separated"),  # text reliable
        }
        return windows, cache, rq16

    def test_returns_per_window_rows(self):
        windows, cache, rq16 = self._setup()
        r = simulate(windows, rq16, cache)
        self.assertEqual(len(r["per_window"]), 3)

    def test_text_only_cpwer_matches_rq16_decisions(self):
        windows, cache, rq16 = self._setup()
        r = simulate(windows, rq16, cache)
        # w0 mixed(1.0), w1 mixed(1.0), w2 separated(1.0) -> mean 1.0
        self.assertAlmostEqual(r["policy_cpwers"]["text_only"]["cpwer"], 1.0)

    def test_emotion_only_cpwer(self):
        windows, cache, rq16 = self._setup()
        r = simulate(windows, rq16, cache)
        # w0 emotion unreliable -> mixed(1.0); w1 reliable -> separated(3.0);
        # w2 reliable -> separated(1.0) -> mean (1.0+3.0+1.0)/3 = 5/3
        self.assertAlmostEqual(r["policy_cpwers"]["emotion_only"]["cpwer"], 5.0 / 3.0, places=5)

    def test_and_policy_cpwer(self):
        windows, cache, rq16 = self._setup()
        r = simulate(windows, rq16, cache)
        # AND: w0 (T or T)=mixed(1.0); w1 (T or F)=mixed(1.0); w2 (F or F)=sep(1.0)
        self.assertAlmostEqual(r["policy_cpwers"]["and_conservative"]["cpwer"], 1.0)

    def test_or_policy_cpwer(self):
        windows, cache, rq16 = self._setup()
        r = simulate(windows, rq16, cache)
        # OR: w0 (T and T)=mixed(1.0); w1 (T and F)=sep(3.0); w2 (F and F)=sep(1.0)
        # mean = (1.0 + 3.0 + 1.0) / 3 = 5/3
        self.assertAlmostEqual(r["policy_cpwers"]["or_aggressive"]["cpwer"], 5.0 / 3.0, places=5)

    def test_disagreement_count(self):
        windows, cache, rq16 = self._setup()
        r = simulate(windows, rq16, cache)
        # w0 T,T agree; w1 T,F disagree; w2 F,F agree -> 1/3
        self.assertEqual(r["disagreement"]["disagree_count"], 1)
        self.assertAlmostEqual(r["disagreement"]["disagree_fraction"], 1.0 / 3.0, places=5)

    def test_decision_counts(self):
        windows, cache, rq16 = self._setup()
        r = simulate(windows, rq16, cache)
        self.assertEqual(r["policy_cpwers"]["text_only"]["decision_counts"]["mixed"], 2)
        self.assertEqual(r["policy_cpwers"]["text_only"]["decision_counts"]["separated"], 1)
        # OR routes mixed only on w0 (both unreliable).
        self.assertEqual(r["policy_cpwers"]["or_aggressive"]["decision_counts"]["mixed"], 1)
        self.assertEqual(r["policy_cpwers"]["or_aggressive"]["decision_counts"]["separated"], 2)

    def test_per_window_row_fields(self):
        windows, cache, rq16 = self._setup()
        r = simulate(windows, rq16, cache)
        row = r["per_window"][0]
        for key in (
            "window_id", "always_mixed_cpwer", "always_separated_cpwer",
            "rq16_corrected_decision", "emotion_reliable", "emotion_has_reading",
            "text_unreliable", "emotion_unreliable",
            "text_only_decision", "emotion_only_decision",
            "and_decision", "or_decision",
            "text_only_cpwer", "emotion_only_cpwer", "and_cpwer", "or_cpwer",
        ):
            self.assertIn(key, row, f"missing {key}")

    def test_emotion_has_reading_flag(self):
        windows, cache, rq16 = self._setup()
        r = simulate(windows, rq16, cache)
        self.assertTrue(all(rw["emotion_has_reading"] for rw in r["per_window"]))

    def test_failopen_window_has_no_reading(self):
        # Add a silent window with no cache entry.
        windows = [_window(0, sep_texts={}, mixed_text="", mixed_cpwer=1.0, sep_cpwer=1.0)]
        r = simulate(windows, {0: _rq16_row(0, "separated")}, {})
        row = r["per_window"][0]
        self.assertFalse(row["emotion_has_reading"])
        self.assertTrue(row["emotion_reliable"])  # fail-open
        self.assertFalse(row["emotion_unreliable"])


# =========================================================================
class TestSmokeRealData(unittest.TestCase):
    """Smoke tests on the real AISHELL-4 + RQ36 + RQ16 artefacts (read-only)."""

    def setUp(self):
        if not AISHELL4_JSON.exists():
            self.skipTest(f"missing {AISHELL4_JSON}")
        if not EMOTION_CACHE_JSON.exists():
            self.skipTest(f"missing {EMOTION_CACHE_JSON}")
        if not RQ16_SIM_JSON.exists():
            self.skipTest(f"missing {RQ16_SIM_JSON}")
        self.windows = load_aishell4_windows()
        self.cache = load_emotion_cache()
        self.rq16 = load_rq16_per_window()
        self.results = simulate(self.windows, self.rq16, self.cache)

    def test_77_windows_loaded(self):
        self.assertEqual(len(self.windows), 77)

    def test_rq16_covers_all_windows(self):
        self.assertEqual(set(self.rq16.keys()), {w["window_id"] for w in self.windows})

    def test_text_only_reproduces_rq16_baseline(self):
        # The text-only policy is RQ16's corrected router; cpWER must match.
        cpwer = self.results["policy_cpwers"]["text_only"]["cpwer"]
        self.assertAlmostEqual(cpwer, TEXT_BASELINE_CPWER, places=4)

    def test_text_only_matches_rq16_reported_value(self):
        # Cross-check against the value stored in RQ16's results JSON.
        rq16_data = json.loads(RQ16_SIM_JSON.read_text(encoding="utf-8"))
        self.assertAlmostEqual(
            self.results["policy_cpwers"]["text_only"]["cpwer"],
            rq16_data["corrected_router_cpwer"],
            places=4,
        )

    def test_emotion_reading_coverage(self):
        n_with = self.results["data_sources"]["emotion_cache"]["n_windows_with_reading"]
        # 67 of 77 windows have a cached emotion reading (10 silent windows lack one).
        self.assertEqual(n_with, 67)
        self.assertEqual(n_with + self.results["data_sources"]["emotion_cache"]["n_windows_missing"], 77)

    def test_disagreement_above_20_percent(self):
        # H53c precondition: signals must disagree on > 20% of windows.
        frac = self.results["disagreement"]["disagree_fraction"]
        self.assertGreater(frac, DISAGREEMENT_THRESHOLD)

    def test_disagreement_cross_tab_sums_to_n(self):
        d = self.results["disagreement"]
        total = d["both_unreliable"] + d["both_reliable"] + d["text_only_unreliable"] + d["emotion_only_unreliable"]
        self.assertEqual(total, d["n"])

    def test_h53c_verdict_supported(self):
        # Pre-registered: disagreement > 20% -> H53c supported on real data.
        self.assertTrue(self.results["hypothesis_verdicts"]["h53c"]["supported"])

    def test_and_policy_is_superset_of_text_only_mixed(self):
        # AND routes mixed on every window text-only does (conservative).
        for row in self.results["per_window"]:
            if row["text_only_decision"] == ROUTE_MIXED:
                self.assertEqual(row["and_decision"], ROUTE_MIXED)

    def test_or_policy_is_subset_of_text_only_mixed(self):
        # OR routes mixed only where text-only does (aggressive).
        for row in self.results["per_window"]:
            if row["or_decision"] == ROUTE_MIXED:
                self.assertEqual(row["text_only_decision"], ROUTE_MIXED)

    def test_results_have_all_policy_keys(self):
        for key in ("text_only", "emotion_only", "and_conservative", "or_aggressive"):
            self.assertIn(key, self.results["policy_cpwers"])
            self.assertIn("cpwer", self.results["policy_cpwers"][key])
            self.assertIn("ci_95", self.results["policy_cpwers"][key])
            self.assertIn("decision_counts", self.results["policy_cpwers"][key])

    def test_hypothesis_verdicts_present(self):
        for h in ("h53a", "h53b", "h53c"):
            self.assertIn(h, self.results["hypothesis_verdicts"])
            self.assertIn("supported", self.results["hypothesis_verdicts"][h])
            self.assertIn("statement", self.results["hypothesis_verdicts"][h])

    def test_per_window_count_matches_windows(self):
        self.assertEqual(len(self.results["per_window"]), len(self.windows))

    def test_label_is_experimental_frontier(self):
        self.assertEqual(self.results["label"], "experimental/frontier")


if __name__ == "__main__":
    unittest.main()
