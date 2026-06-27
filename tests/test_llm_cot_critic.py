"""Tests for the RQ52 chain-of-thought LLM critic (experimental/frontier).

Pin the PURE, model-free logic with an INJECTED fake LLM (so tests run offline
without ollama): CoT prompt construction, think-stripping, verdict parsing
(VERDICT/CONFIDENCE lines + prose fallback), hallucination-score mapping,
ROC AUC, threshold calibration, evaluation, subgroup sensitivity, FP rate,
bootstrap CIs, and cache load/save/keying. The real deepseek-r1/ollama backend
is exercised only by the analysis driver, never in unit tests.
"""
from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.llm_cot_critic import (
    CATASTROPHIC_CPWER,
    bootstrap_ci,
    build_cot_prompt,
    cache_key,
    calibrate_threshold_at_specificity,
    evaluate_at_threshold,
    false_positive_rate,
    hallucination_score,
    judge_window_cot,
    load_cache,
    ollama_available,
    parse_cot_verdict,
    roc_auc,
    save_cache,
    strip_think,
    subgroup_sensitivity,
)


def fake_llm(response: str):
    """Return an LLMFn that always replies with `response` (ignores the prompt)."""
    return lambda prompt: response


# --------------------------------------------------------------------- strip_think
class TestStripThink(unittest.TestCase):
    def test_removes_think_block(self) -> None:
        self.assertEqual(
            strip_think("<think>reasoning here</think>\nVERDICT: NO").strip(),
            "VERDICT: NO")

    def test_no_think_passthrough(self) -> None:
        self.assertEqual(strip_think("VERDICT: YES"), "VERDICT: YES")

    def test_unclosed_think_is_dropped(self) -> None:
        self.assertEqual(strip_think("<think>still thinking and cut off").strip(), "")

    def test_multiline_think(self) -> None:
        self.assertEqual(
            strip_think("<think>line1\nline2\nline3</think>VERDICT: YES").strip(),
            "VERDICT: YES")


# ------------------------------------------------------------- prompt construction
class TestBuildCoTPrompt(unittest.TestCase):
    def test_prompt_contains_transcript(self) -> None:
        p = build_cot_prompt("我说一下那些男生后")
        self.assertIn("我说一下那些男生后", p)
        self.assertIn("Transcript:", p)

    def test_prompt_has_five_steps(self) -> None:
        p = build_cot_prompt("some text")
        self.assertIn("Step 1:", p)
        self.assertIn("Step 2:", p)
        self.assertIn("Step 3:", p)
        self.assertIn("Step 4:", p)
        self.assertIn("Step 5:", p)

    def test_prompt_step1_language(self) -> None:
        p = build_cot_prompt("text")
        self.assertIn("language", p.lower())
        self.assertIn("monolingual", p.lower())

    def test_prompt_step2_repetition(self) -> None:
        p = build_cot_prompt("text")
        self.assertIn("repetition", p.lower())

    def test_prompt_step3_coherence(self) -> None:
        p = build_cot_prompt("text")
        self.assertIn("semantic coherence", p.lower())

    def test_prompt_step4_insertion(self) -> None:
        p = build_cot_prompt("text")
        self.assertIn("insertion", p.lower())

    def test_prompt_requests_yes_no_verdict(self) -> None:
        p = build_cot_prompt("text")
        self.assertIn("YES", p)
        self.assertIn("NO", p)
        self.assertIn("hallucinated", p.lower())

    def test_prompt_has_verdict_confidence_format(self) -> None:
        p = build_cot_prompt("text")
        self.assertIn("VERDICT:", p)
        self.assertIn("CONFIDENCE:", p)


# ------------------------------------------------------------- verdict parsing
class TestParseCotVerdict(unittest.TestCase):
    def test_verdict_yes(self) -> None:
        r = parse_cot_verdict("Step 1...\nVERDICT: YES\nCONFIDENCE: 0.8")
        self.assertTrue(r["hallucinated"])
        self.assertAlmostEqual(r["confidence"], 0.8)

    def test_verdict_no(self) -> None:
        r = parse_cot_verdict("Step 1...\nVERDICT: NO\nCONFIDENCE: 0.9")
        self.assertFalse(r["hallucinated"])
        self.assertAlmostEqual(r["confidence"], 0.9)

    def test_verdict_with_think_block(self) -> None:
        r = parse_cot_verdict(
            "<think>step by step reasoning</think>\nVERDICT: YES\nCONFIDENCE: 0.7")
        self.assertTrue(r["hallucinated"])
        self.assertAlmostEqual(r["confidence"], 0.7)

    def test_verdict_case_insensitive(self) -> None:
        r = parse_cot_verdict("verdict: yes\nconfidence: 0.6")
        self.assertTrue(r["hallucinated"])
        self.assertAlmostEqual(r["confidence"], 0.6)

    def test_verdict_chinese_aliases(self) -> None:
        r = parse_cot_verdict("VERDICT: 是\nCONFIDENCE: 0.5")
        self.assertTrue(r["hallucinated"])
        r2 = parse_cot_verdict("VERDICT: 否\nCONFIDENCE: 0.5")
        self.assertFalse(r2["hallucinated"])

    def test_verdict_clean_alias(self) -> None:
        r = parse_cot_verdict("VERDICT: clean\nCONFIDENCE: 0.5")
        self.assertFalse(r["hallucinated"])

    def test_verdict_hallucinated_alias(self) -> None:
        r = parse_cot_verdict("VERDICT: hallucinated\nCONFIDENCE: 0.5")
        self.assertTrue(r["hallucinated"])

    def test_confidence_clamped_high(self) -> None:
        r = parse_cot_verdict("VERDICT: YES\nCONFIDENCE: 1.5")
        self.assertTrue(r["hallucinated"])
        self.assertAlmostEqual(r["confidence"], 1.0)

    def test_confidence_clamped_low(self) -> None:
        r = parse_cot_verdict("VERDICT: NO\nCONFIDENCE: -0.3")
        self.assertFalse(r["hallucinated"])
        self.assertAlmostEqual(r["confidence"], 0.0)

    def test_missing_verdict_defaults_false(self) -> None:
        r = parse_cot_verdict("just some reasoning with no verdict line")
        self.assertFalse(r["hallucinated"])
        self.assertAlmostEqual(r["confidence"], 0.5)

    def test_missing_confidence_defaults_half(self) -> None:
        r = parse_cot_verdict("VERDICT: YES")
        self.assertTrue(r["hallucinated"])
        self.assertAlmostEqual(r["confidence"], 0.5)

    def test_fallback_prose_yes_last(self) -> None:
        # no VERDICT: line; prose mentions both yes and no, yes appears last
        r = parse_cot_verdict("the answer is no I think, actually yes")
        self.assertTrue(r["hallucinated"])

    def test_fallback_prose_no_last(self) -> None:
        r = parse_cot_verdict("the answer is yes I think, actually no")
        self.assertFalse(r["hallucinated"])

    def test_verdict_raw_captured(self) -> None:
        r = parse_cot_verdict("VERDICT: YES\nCONFIDENCE: 0.8")
        self.assertEqual(r["verdict_raw"], "YES")


# ------------------------------------------------------------- hallucination_score
class TestHallucinationScore(unittest.TestCase):
    def test_hallucinated_high_conf(self) -> None:
        self.assertAlmostEqual(hallucination_score(True, 0.9), 0.9)

    def test_clean_high_conf(self) -> None:
        self.assertAlmostEqual(hallucination_score(False, 0.9), 0.1)

    def test_hallucinated_low_conf(self) -> None:
        self.assertAlmostEqual(hallucination_score(True, 0.2), 0.2)

    def test_confidence_clamped(self) -> None:
        self.assertAlmostEqual(hallucination_score(True, 1.5), 1.0)
        self.assertAlmostEqual(hallucination_score(False, -0.5), 1.0)

    def test_score_in_unit_interval(self) -> None:
        for h in (True, False):
            for c in (0.0, 0.25, 0.5, 0.75, 1.0):
                s = hallucination_score(h, c)
                self.assertGreaterEqual(s, 0.0)
                self.assertLessEqual(s, 1.0)


# ------------------------------------------------------------- ROC AUC
class TestRocAuc(unittest.TestCase):
    def test_perfect_separation(self) -> None:
        # all positives higher than all negatives
        scores = [0.9, 0.8, 0.3, 0.2]
        labels = [1, 1, 0, 0]
        self.assertAlmostEqual(roc_auc(scores, labels), 1.0)

    def test_perfect_inversion(self) -> None:
        # all positives LOWER than all negatives -> AUC = 0
        scores = [0.1, 0.2, 0.8, 0.9]
        labels = [1, 1, 0, 0]
        self.assertAlmostEqual(roc_auc(scores, labels), 0.0)

    def test_random_overlap(self) -> None:
        # positives 0.4, 0.1 vs negatives 0.3, 0.2 -> 2 of 4 pairs have pos > neg -> AUC = 0.5
        scores = [0.4, 0.3, 0.2, 0.1]
        labels = [1, 0, 0, 1]
        self.assertAlmostEqual(roc_auc(scores, labels), 0.5)

    def test_ties_count_as_half(self) -> None:
        # all scores equal -> AUC = 0.5 (all pairs are ties)
        scores = [0.5, 0.5, 0.5, 0.5]
        labels = [1, 1, 0, 0]
        self.assertAlmostEqual(roc_auc(scores, labels), 0.5)

    def test_empty_class_returns_half(self) -> None:
        self.assertAlmostEqual(roc_auc([0.1, 0.2], [1, 1]), 0.5)
        self.assertAlmostEqual(roc_auc([0.1, 0.2], [0, 0]), 0.5)

    def test_partial_separation(self) -> None:
        # 1 of 2 positives above both negatives, 1 below -> AUC = 0.5
        scores = [0.9, 0.1, 0.4, 0.3]
        labels = [1, 1, 0, 0]
        self.assertAlmostEqual(roc_auc(scores, labels), 0.5)


# ------------------------------------------------------------- calibration + evaluation
class TestCalibration(unittest.TestCase):
    def test_finds_90pct_spec(self) -> None:
        neg = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        pos = [1.0, 0.95]
        cal = calibrate_threshold_at_specificity(neg, pos, target_spec=0.9)
        self.assertGreaterEqual(cal["specificity"], 0.9 - 1e-9)
        # threshold 0.9 -> 1 FP (0.9 itself), spec = 0.9, catches both positives
        self.assertAlmostEqual(cal["threshold"], 0.9)

    def test_no_threshold_meets_spec(self) -> None:
        # all negatives at max score -> cannot reach 90% spec
        neg = [1.0, 1.0, 1.0]
        cal = calibrate_threshold_at_specificity(neg, [1.0], target_spec=0.9)
        self.assertAlmostEqual(cal["threshold"], float("inf"))
        self.assertAlmostEqual(cal["specificity"], 1.0)

    def test_empty_negatives(self) -> None:
        cal = calibrate_threshold_at_specificity([], [0.5], target_spec=0.9)
        self.assertAlmostEqual(cal["threshold"], float("inf"))


class TestEvaluateAtThreshold(unittest.TestCase):
    def test_perfect_detector(self) -> None:
        scores = [0.9, 0.8, 0.2, 0.1]
        labels = [1, 1, 0, 0]
        r = evaluate_at_threshold(scores, labels, 0.5)
        self.assertEqual(r["tp"], 2)
        self.assertEqual(r["fp"], 0)
        self.assertEqual(r["tn"], 2)
        self.assertEqual(r["fn"], 0)
        self.assertAlmostEqual(r["sensitivity"], 1.0)
        self.assertAlmostEqual(r["specificity"], 1.0)

    def test_all_flagged(self) -> None:
        scores = [0.9, 0.8]
        labels = [1, 0]
        r = evaluate_at_threshold(scores, labels, 0.0)
        self.assertEqual(r["tp"], 1)
        self.assertEqual(r["fp"], 1)
        self.assertAlmostEqual(r["sensitivity"], 1.0)
        self.assertAlmostEqual(r["specificity"], 0.0)

    def test_precision(self) -> None:
        scores = [0.9, 0.8, 0.7]
        labels = [1, 0, 0]
        r = evaluate_at_threshold(scores, labels, 0.65)
        # flags all 3 (0.9, 0.8, 0.7 >= 0.65): tp=1, fp=2 -> precision = 1/3
        self.assertAlmostEqual(r["precision"], 1.0 / 3.0)


class TestFalsePositiveRate(unittest.TestCase):
    def test_fp_rate(self) -> None:
        scores = [0.9, 0.8, 0.6, 0.5]
        labels = [1, 1, 0, 0]
        # threshold 0.65 -> flags 0.9, 0.8 (both pos); negatives 0.6, 0.5 below -> fp = 0
        self.assertAlmostEqual(false_positive_rate(scores, labels, 0.65), 0.0)
        # threshold 0.45 -> flags all 4; fp = 2/2 = 1.0
        self.assertAlmostEqual(false_positive_rate(scores, labels, 0.45), 1.0)

    def test_fp_rate_no_negatives(self) -> None:
        self.assertAlmostEqual(false_positive_rate([0.9], [1], 0.5), 0.0)


class TestSubgroupSensitivity(unittest.TestCase):
    def test_mode_s_subgroup(self) -> None:
        scores = [0.9, 0.4, 0.8, 0.3]
        mask = [True, True, False, False]
        # threshold 0.5 -> flags 0.9 (mode S), 0.8 (not mode S)
        r = subgroup_sensitivity(scores, mask, 0.5)
        self.assertAlmostEqual(r["sensitivity"], 0.5)
        self.assertEqual(r["tp"], 1)
        self.assertEqual(r["n"], 2)

    def test_empty_subgroup(self) -> None:
        r = subgroup_sensitivity([0.9], [False], 0.5)
        self.assertAlmostEqual(r["sensitivity"], 0.0)
        self.assertEqual(r["n"], 0)


# ------------------------------------------------------------- bootstrap CI
class TestBootstrapCI(unittest.TestCase):
    def test_sensitivity_ci_bounds(self) -> None:
        scores = np.array([0.9, 0.4, 0.55, 0.2, 0.6, 0.1])
        labels = np.array([1.0, 1.0, 1.0, 0.0, 0.0, 0.0])
        lo, hi = bootstrap_ci(scores, labels, threshold=0.5, metric="sensitivity",
                              n_boot=500, seed=42)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)
        self.assertGreaterEqual(hi, lo)

    def test_specificity_ci_bounds(self) -> None:
        scores = np.array([0.9, 0.8, 0.1, 0.2])
        labels = np.array([1.0, 1.0, 0.0, 0.0])
        lo, hi = bootstrap_ci(scores, labels, threshold=0.5, metric="specificity",
                              n_boot=500, seed=42)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)


# ------------------------------------------------------------- cache
class TestCache(unittest.TestCase):
    def test_cache_key_stable(self) -> None:
        self.assertEqual(cache_key("hello"), cache_key("hello"))
        self.assertNotEqual(cache_key("hello"), cache_key("world"))

    def test_cache_key_strips_whitespace(self) -> None:
        self.assertEqual(cache_key("  hello  "), cache_key("hello"))

    def test_save_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "cache.json"
            cache = {"key1": {"hallucinated": True, "confidence": 0.8, "raw": "x"}}
            save_cache(p, cache)
            loaded = load_cache(p)
            self.assertEqual(loaded, cache)

    def test_load_missing_returns_empty(self) -> None:
        self.assertEqual(load_cache(Path("/nonexistent/path/cache.json")), {})

    def test_load_malformed_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "cache.json"
            p.write_text("{not valid json", encoding="utf-8")
            self.assertEqual(load_cache(p), {})


# ------------------------------------------------------------- judge_window_cot
class TestJudgeWindowCot(unittest.TestCase):
    def test_uses_fake_llm(self) -> None:
        llm = fake_llm("<think>reasoning</think>\nVERDICT: YES\nCONFIDENCE: 0.7")
        r = judge_window_cot("some text", llm)
        self.assertTrue(r["hallucinated"])
        self.assertAlmostEqual(r["confidence"], 0.7)
        self.assertIn("raw", r)

    def test_empty_transcript_short_circuit(self) -> None:
        call_count = [0]

        def counting_llm(prompt: str) -> str:
            call_count[0] += 1
            return "VERDICT: NO"

        r = judge_window_cot("", counting_llm)
        self.assertEqual(call_count[0], 0)
        self.assertFalse(r["hallucinated"])
        self.assertEqual(r["reason"], "empty transcript")

    def test_whitespace_only_short_circuit(self) -> None:
        call_count = [0]

        def counting_llm(prompt: str) -> str:
            call_count[0] += 1
            return "VERDICT: NO"

        r = judge_window_cot("   \n  ", counting_llm)
        self.assertEqual(call_count[0], 0)
        self.assertFalse(r["hallucinated"])


# ------------------------------------------------------------- ollama_available (offline)
class TestOllamaAvailable(unittest.TestCase):
    def test_returns_bool_without_raising(self) -> None:
        # ollama is not guaranteed running in CI; just check it returns a bool
        result = ollama_available(host="http://localhost:1", model="deepseek-r1:7b")
        self.assertIsInstance(result, bool)


if __name__ == "__main__":
    unittest.main()
