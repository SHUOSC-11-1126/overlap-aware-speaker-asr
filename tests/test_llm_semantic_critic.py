"""Tests for the RQ34 LLM semantic critic (experimental/frontier).

Pin the PURE, model-free logic with an INJECTED fake LLM (so tests run offline
without ollama): think-stripping, JSON/regex response parsing, hallucination-score
mapping, char n-gram KL-divergence fallback, threshold calibration, evaluation at
threshold, subgroup sensitivity, and bootstrap CIs. The real deepseek-r1/ollama
backend is exercised only by the driver, never in unit tests.
"""
from __future__ import annotations

import math
import unittest

import numpy as np

from src.llm_semantic_critic import (
    _extract_json_object,
    average_distributions,
    bootstrap_sensitivity_ci,
    bootstrap_specificity_ci,
    build_critic_prompt,
    build_reference_distribution,
    calibrate_threshold_at_specificity,
    char_distribution,
    char_ngrams,
    compute_anomaly_score,
    compression_ratio,
    evaluate_at_threshold,
    hallucination_score,
    judge_window,
    kl_divergence,
    label_window,
    language_id_entropy,
    length_ratio,
    ollama_available,
    parse_llm_response,
    separated_concat,
    subgroup_sensitivity,
    strip_think,
)


def fake_llm(response: str):
    """Return an LLMFn that always replies with `response` (ignores the prompt)."""
    return lambda prompt: response


# --------------------------------------------------------------------- strip_think
class TestStripThink(unittest.TestCase):
    def test_removes_think_block(self) -> None:
        self.assertEqual(
            strip_think("<think>reasoning here</think>\n{\"hallucinated\": true}").strip(),
            "{\"hallucinated\": true}",
        )

    def test_no_think_passthrough(self) -> None:
        self.assertEqual(strip_think("{\"hallucinated\": false}"), "{\"hallucinated\": false}")

    def test_unclosed_think_is_dropped(self) -> None:
        # a truncated/unclosed think block should not leak reasoning into the answer
        self.assertEqual(strip_think("<think>still thinking and cut off").strip(), "")

    def test_multiline_think(self) -> None:
        self.assertEqual(
            strip_think("<think>line1\nline2\nline3</think>answer").strip(),
            "answer",
        )


# ----------------------------------------------------------------- prompt building
class TestBuildCriticPrompt(unittest.TestCase):
    def test_prompt_contains_transcript(self) -> None:
        p = build_critic_prompt("我说一下那些男生后")
        self.assertIn("我说一下那些男生后", p)
        self.assertIn("Transcript:", p)

    def test_prompt_requests_json(self) -> None:
        p = build_critic_prompt("some text")
        self.assertIn("JSON", p)
        self.assertIn("hallucinated", p)
        self.assertIn("confidence", p)

    def test_prompt_contains_three_criteria(self) -> None:
        p = build_critic_prompt("text")
        self.assertIn("semantic sense", p)
        self.assertIn("repetitive", p)
        self.assertIn("character patterns", p)


# ------------------------------------------------------------- JSON extraction
class TestExtractJsonObject(unittest.TestCase):
    def test_simple_object(self) -> None:
        self.assertEqual(_extract_json_object('{"a": 1}'), '{"a": 1}')

    def test_nested_object(self) -> None:
        self.assertEqual(_extract_json_object('{"a": {"b": 2}}'), '{"a": {"b": 2}}')

    def test_with_surrounding_text(self) -> None:
        self.assertEqual(
            _extract_json_object('Here is the result: {"x": true} done'),
            '{"x": true}',
        )

    def test_braces_inside_strings(self) -> None:
        self.assertEqual(
            _extract_json_object('{"reason": "has a } char"}'),
            '{"reason": "has a } char"}',
        )

    def test_no_braces(self) -> None:
        self.assertIsNone(_extract_json_object("no braces here"))

    def test_unbalanced(self) -> None:
        self.assertIsNone(_extract_json_object('{"a": 1'))


# ------------------------------------------------------------- response parsing
class TestParseLlmResponse(unittest.TestCase):
    def test_clean_json(self) -> None:
        r = parse_llm_response('{"hallucinated": true, "confidence": 0.9, "reason": "repetitive"}')
        self.assertTrue(r["hallucinated"])
        self.assertAlmostEqual(r["confidence"], 0.9)
        self.assertEqual(r["reason"], "repetitive")

    def test_json_with_think(self) -> None:
        r = parse_llm_response('<think>analyzing...</think>\n{"hallucinated": false, "confidence": 0.8}')
        self.assertFalse(r["hallucinated"])
        self.assertAlmostEqual(r["confidence"], 0.8)

    def test_json_false_as_string(self) -> None:
        r = parse_llm_response('{"hallucinated": "false", "confidence": "0.7"}')
        self.assertFalse(r["hallucinated"])
        self.assertAlmostEqual(r["confidence"], 0.7)

    def test_regex_fallback(self) -> None:
        # no valid JSON, but fields present in prose
        r = parse_llm_response("The transcript is hallucinated: true with confidence: 0.85")
        self.assertTrue(r["hallucinated"])
        self.assertAlmostEqual(r["confidence"], 0.85)

    def test_regex_fallback_false(self) -> None:
        r = parse_llm_response("hallucinated: false, confidence: 0.6")
        self.assertFalse(r["hallucinated"])
        self.assertAlmostEqual(r["confidence"], 0.6)

    def test_no_fields_defaults(self) -> None:
        r = parse_llm_response("I cannot determine the answer.")
        self.assertFalse(r["hallucinated"])
        self.assertAlmostEqual(r["confidence"], 0.5)
        self.assertEqual(r["reason"], "")

    def test_confidence_clamped_high(self) -> None:
        r = parse_llm_response('{"hallucinated": true, "confidence": 1.5}')
        self.assertAlmostEqual(r["confidence"], 1.0)

    def test_confidence_clamped_low(self) -> None:
        r = parse_llm_response('{"hallucinated": true, "confidence": -0.3}')
        self.assertAlmostEqual(r["confidence"], 0.0)

    def test_json_with_quoted_reason(self) -> None:
        r = parse_llm_response('{"hallucinated": true, "confidence": 0.95, "reason": "suspicious repetition of 那個"}')
        self.assertTrue(r["hallucinated"])
        self.assertEqual(r["reason"], "suspicious repetition of 那個")


# ------------------------------------------------------------- hallucination score
class TestHallucinationScore(unittest.TestCase):
    def test_hallucinated_high_confidence(self) -> None:
        self.assertAlmostEqual(hallucination_score(True, 0.95), 0.95)

    def test_not_hallucinated_high_confidence(self) -> None:
        self.assertAlmostEqual(hallucination_score(False, 0.95), 0.05)

    def test_mid_confidence(self) -> None:
        self.assertAlmostEqual(hallucination_score(True, 0.5), 0.5)
        self.assertAlmostEqual(hallucination_score(False, 0.5), 0.5)

    def test_clamping(self) -> None:
        self.assertAlmostEqual(hallucination_score(True, 1.5), 1.0)
        self.assertAlmostEqual(hallucination_score(False, -0.5), 1.0)  # 1 - (-0.5) clamped

    def test_score_range(self) -> None:
        for h in (True, False):
            for c in (0.0, 0.25, 0.5, 0.75, 1.0):
                s = hallucination_score(h, c)
                self.assertGreaterEqual(s, 0.0)
                self.assertLessEqual(s, 1.0)


# ------------------------------------------------------------- judge_window
class TestJudgeWindow(unittest.TestCase):
    def test_parses_injected_response(self) -> None:
        llm = fake_llm('<think>ok</think>\n{"hallucinated": true, "confidence": 0.9, "reason": "rep"}')
        r = judge_window("some transcript", llm)
        self.assertTrue(r["hallucinated"])
        self.assertAlmostEqual(r["confidence"], 0.9)
        self.assertIn("raw", r)

    def test_empty_transcript_no_llm_call(self) -> None:
        called = []

        def llm(prompt: str) -> str:
            called.append(prompt)
            return "should not be called"

        r = judge_window("", llm)
        self.assertFalse(r["hallucinated"])
        self.assertEqual(len(called), 0)

    def test_whitespace_only_transcript(self) -> None:
        r = judge_window("   \n  ", fake_llm("nope"))
        self.assertFalse(r["hallucinated"])


# ------------------------------------------------------------- char n-grams
class TestCharNgrams(unittest.TestCase):
    def test_basic(self) -> None:
        counts = char_ngrams("abcd", n=3)
        self.assertEqual(counts, {"abc": 1, "bcd": 1})

    def test_short_text(self) -> None:
        counts = char_ngrams("ab", n=3)
        self.assertEqual(counts, {"ab": 1})

    def test_whitespace_stripped(self) -> None:
        counts = char_ngrams("a b c", n=2)
        self.assertEqual(counts, {"ab": 1, "bc": 1})

    def test_repeats(self) -> None:
        counts = char_ngrams("aaa", n=2)
        self.assertEqual(counts, {"aa": 2})

    def test_empty(self) -> None:
        self.assertEqual(char_ngrams("", n=3), {})


class TestCharDistribution(unittest.TestCase):
    def test_normalized(self) -> None:
        dist = char_distribution("aabb", n=1)
        self.assertAlmostEqual(dist["a"], 0.5)
        self.assertAlmostEqual(dist["b"], 0.5)

    def test_sums_to_one(self) -> None:
        dist = char_distribution("abcabc", n=2)
        self.assertAlmostEqual(sum(dist.values()), 1.0)

    def test_with_vocab(self) -> None:
        dist = char_distribution("aab", n=1, vocab={"a", "b", "c"})
        self.assertAlmostEqual(dist["a"], 2 / 3)
        self.assertAlmostEqual(dist["b"], 1 / 3)
        self.assertAlmostEqual(dist["c"], 0.0)

    def test_empty(self) -> None:
        self.assertEqual(char_distribution("", n=3), {})


class TestAverageDistributions(unittest.TestCase):
    def test_average(self) -> None:
        d1 = {"a": 0.5, "b": 0.5}
        d2 = {"a": 0.25, "c": 0.75}
        avg = average_distributions([d1, d2])
        self.assertAlmostEqual(avg["a"], 0.375)
        self.assertAlmostEqual(avg["b"], 0.25)
        self.assertAlmostEqual(avg["c"], 0.375)

    def test_empty(self) -> None:
        self.assertEqual(average_distributions([]), {})

    def test_sums_to_one(self) -> None:
        d1 = {"a": 1.0}
        d2 = {"b": 1.0}
        avg = average_distributions([d1, d2])
        self.assertAlmostEqual(sum(avg.values()), 1.0)


class TestKlDivergence(unittest.TestCase):
    def test_identical_is_zero(self) -> None:
        d = {"a": 0.5, "b": 0.5}
        self.assertAlmostEqual(kl_divergence(d, d), 0.0, places=5)

    def test_different_is_positive(self) -> None:
        p = {"a": 0.9, "b": 0.1}
        q = {"a": 0.5, "b": 0.5}
        self.assertGreater(kl_divergence(p, q), 0.0)

    def test_asymmetric(self) -> None:
        p = {"a": 0.9, "b": 0.1}
        q = {"a": 0.5, "b": 0.5}
        # KL(p||q) != KL(q||p) in general
        self.assertNotAlmostEqual(kl_divergence(p, q), kl_divergence(q, p), places=3)

    def test_empty(self) -> None:
        self.assertAlmostEqual(kl_divergence({}, {}), 0.0)

    def test_disjoint_keys(self) -> None:
        p = {"a": 1.0}
        q = {"b": 1.0}
        # with smoothing, KL is large but finite
        kl = kl_divergence(p, q)
        self.assertGreater(kl, 0.0)
        self.assertTrue(math.isfinite(kl))


class TestComputeAnomalyScore(unittest.TestCase):
    def test_identical_text_zero(self) -> None:
        ref = char_distribution("abcabc", n=2)
        score = compute_anomaly_score("abcabc", ref, n=2)
        self.assertAlmostEqual(score, 0.0, places=4)

    def test_different_text_positive(self) -> None:
        ref = char_distribution("aaaa", n=1)
        score = compute_anomaly_score("bbbb", ref, n=1)
        self.assertGreater(score, 0.0)

    def test_empty_text_zero(self) -> None:
        ref = char_distribution("abc", n=2)
        self.assertAlmostEqual(compute_anomaly_score("", ref, n=2), 0.0)


class TestBuildReferenceDistribution(unittest.TestCase):
    def test_basic(self) -> None:
        ref = build_reference_distribution(["aabb", "ccdd"], n=1)
        self.assertIn("a", ref)
        self.assertIn("c", ref)
        self.assertAlmostEqual(sum(ref.values()), 1.0)

    def test_skips_empty(self) -> None:
        ref = build_reference_distribution(["", "  ", "ab"], n=1)
        self.assertAlmostEqual(sum(ref.values()), 1.0)


# ------------------------------------------------------------- surface features
class TestSurfaceFeatures(unittest.TestCase):
    def test_language_id_entropy_pure_script(self) -> None:
        # all-Han text has low entropy (single script category)
        ent = language_id_entropy("你好世界")
        self.assertLess(ent, 0.1)

    def test_language_id_entropy_mixed(self) -> None:
        # mixed scripts have higher entropy
        ent = language_id_entropy("你好 Hello 123")
        self.assertGreater(ent, 1.0)

    def test_compression_ratio_repetitive(self) -> None:
        # long repetition compresses very well → high CR
        cr = compression_ratio("a" * 200)
        self.assertGreater(cr, 2.0)

    def test_compression_ratio_normal(self) -> None:
        cr = compression_ratio("这是一段正常的中文文本")
        self.assertLess(cr, 2.0)

    def test_compression_ratio_empty(self) -> None:
        self.assertEqual(compression_ratio(""), 0.0)


class TestLabelWindow(unittest.TestCase):
    def _window(self, sep_texts: dict[str, str], sep_total: int = None,
                mixed_len: int = 50, sep_cpwer: float = 2.0) -> dict:
        if sep_total is None:
            sep_total = sum(len(t) for t in sep_texts.values())
        return {
            "window_id": 0,
            "always_separated_cpwer": sep_cpwer,
            "always_mixed_cpwer": 1.0,
            "separated_text_per_speaker": sep_texts,
            "separated_total_length": sep_total,
            "mixed_text_length": mixed_len,
            "num_speakers": len(sep_texts),
        }

    def test_hallucinated_label(self) -> None:
        # mixed-script text has high lang-id entropy → diverse hallucination, not Mode S
        w = self._window({"001-M": "你好 Hello World 123"}, sep_cpwer=2.0)
        lbl = label_window(w)
        self.assertTrue(lbl["hallucinated"])
        self.assertGreater(lbl["lang_id_entropy"], 0.409)
        self.assertFalse(lbl["mode_s"])
        self.assertTrue(lbl["diverse_hallucination"])

    def test_non_hallucinated_label(self) -> None:
        w = self._window({"001-M": "你好"}, sep_cpwer=0.5)
        lbl = label_window(w)
        self.assertFalse(lbl["hallucinated"])

    def test_separated_concat(self) -> None:
        w = self._window({"001-M": "你好", "002-M": "世界"})
        lbl = label_window(w)
        self.assertEqual(lbl["separated_text"], "你好世界")


# ------------------------------------------------------------- calibration
class TestCalibrateThreshold(unittest.TestCase):
    def test_basic(self) -> None:
        # 10 neg scores, target spec 0.8 => max_fp = 2
        neg = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
        pos = [0.85]
        result = calibrate_threshold_at_specificity(neg, pos, target_spec=0.8)
        # max_fp = 2, smallest t with <= 2 neg >= t: t=0.85 (neg >= 0.85 = {0.9, 0.95} = 2)
        self.assertAlmostEqual(result["threshold"], 0.85)
        self.assertAlmostEqual(result["specificity"], 0.8)

    def test_pos_between_negs(self) -> None:
        # pos score between two negs can be the optimal threshold
        neg = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
        pos = [0.82]  # between 0.8 and 0.9
        result = calibrate_threshold_at_specificity(neg, pos, target_spec=0.8)
        # max_fp = 2, t=0.82: neg >= 0.82 = {0.9, 0.95} = 2 FPs. Valid!
        self.assertAlmostEqual(result["threshold"], 0.82)
        self.assertAlmostEqual(result["specificity"], 0.8)

    def test_no_valid_threshold(self) -> None:
        # all negs are very high; even the highest gives too many FPs
        neg = [0.9, 0.9, 0.9, 0.9, 0.9]
        result = calibrate_threshold_at_specificity(neg, target_spec=0.8)
        # max_fp = 1, but even t=0.9 gives fp=5 > 1. So threshold = inf.
        self.assertEqual(result["threshold"], float("inf"))
        self.assertAlmostEqual(result["specificity"], 1.0)

    def test_empty_neg(self) -> None:
        result = calibrate_threshold_at_specificity([], target_spec=0.9)
        self.assertEqual(result["threshold"], float("inf"))

    def test_high_specificity(self) -> None:
        neg = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
        pos = [0.85]
        # target spec 0.9 => max_fp = 1
        result = calibrate_threshold_at_specificity(neg, pos, target_spec=0.9)
        # smallest t with <= 1 neg >= t: t=0.9 (neg >= 0.9 = {0.9, 0.95} = 2 > 1).
        # t=0.95: neg >= 0.95 = {0.95} = 1 <= 1. Valid.
        self.assertAlmostEqual(result["threshold"], 0.95)
        self.assertAlmostEqual(result["specificity"], 0.9)


# ------------------------------------------------------------- evaluation
class TestEvaluateAtThreshold(unittest.TestCase):
    def test_perfect(self) -> None:
        scores = [0.9, 0.8, 0.1, 0.2]
        labels = [1, 1, 0, 0]
        r = evaluate_at_threshold(scores, labels, 0.5)
        self.assertEqual(r["tp"], 2)
        self.assertEqual(r["fp"], 0)
        self.assertEqual(r["tn"], 2)
        self.assertEqual(r["fn"], 0)
        self.assertAlmostEqual(r["sensitivity"], 1.0)
        self.assertAlmostEqual(r["specificity"], 1.0)

    def test_mixed(self) -> None:
        scores = [0.9, 0.3, 0.6, 0.1]
        labels = [1, 1, 0, 0]
        r = evaluate_at_threshold(scores, labels, 0.5)
        self.assertEqual(r["tp"], 1)
        self.assertEqual(r["fp"], 1)
        self.assertEqual(r["tn"], 1)
        self.assertEqual(r["fn"], 1)
        self.assertAlmostEqual(r["sensitivity"], 0.5)
        self.assertAlmostEqual(r["specificity"], 0.5)

    def test_flag_nothing(self) -> None:
        scores = [0.9, 0.8]
        labels = [1, 0]
        r = evaluate_at_threshold(scores, labels, float("inf"))
        self.assertEqual(r["tp"], 0)
        self.assertEqual(r["fp"], 0)
        self.assertAlmostEqual(r["sensitivity"], 0.0)
        self.assertAlmostEqual(r["specificity"], 1.0)


class TestSubgroupSensitivity(unittest.TestCase):
    def test_basic(self) -> None:
        scores = [0.9, 0.8, 0.1, 0.2]
        mask = [True, True, False, False]
        r = subgroup_sensitivity(scores, mask, 0.5)
        self.assertAlmostEqual(r["sensitivity"], 1.0)
        self.assertEqual(r["tp"], 2)
        self.assertEqual(r["n"], 2)

    def test_partial(self) -> None:
        scores = [0.9, 0.3, 0.1]
        mask = [True, True, False]
        r = subgroup_sensitivity(scores, mask, 0.5)
        self.assertAlmostEqual(r["sensitivity"], 0.5)
        self.assertEqual(r["tp"], 1)
        self.assertEqual(r["n"], 2)

    def test_empty_subgroup(self) -> None:
        r = subgroup_sensitivity([0.9, 0.1], [False, False], 0.5)
        self.assertAlmostEqual(r["sensitivity"], 0.0)
        self.assertEqual(r["n"], 0)


# ------------------------------------------------------------- bootstrap CI
class TestBootstrapCI(unittest.TestCase):
    def test_sensitivity_ci_range(self) -> None:
        scores = np.array([0.9, 0.8, 0.1, 0.2])
        labels = np.array([1.0, 1.0, 0.0, 0.0])
        lo, hi = bootstrap_sensitivity_ci(scores, labels, 0.5, n_boot=500, seed=42)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)
        self.assertLessEqual(lo, hi)

    def test_specificity_ci_range(self) -> None:
        scores = np.array([0.9, 0.8, 0.1, 0.2])
        labels = np.array([1.0, 1.0, 0.0, 0.0])
        lo, hi = bootstrap_specificity_ci(scores, labels, 0.5, n_boot=500, seed=42)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)
        self.assertLessEqual(lo, hi)

    def test_no_positives(self) -> None:
        scores = np.array([0.1, 0.2])
        labels = np.array([0.0, 0.0])
        lo, hi = bootstrap_sensitivity_ci(scores, labels, 0.5, n_boot=100, seed=42)
        self.assertEqual(lo, 0.0)
        self.assertEqual(hi, 0.0)

    def test_deterministic(self) -> None:
        scores = np.array([0.9, 0.8, 0.1, 0.2])
        labels = np.array([1.0, 1.0, 0.0, 0.0])
        r1 = bootstrap_sensitivity_ci(scores, labels, 0.5, n_boot=200, seed=42)
        r2 = bootstrap_sensitivity_ci(scores, labels, 0.5, n_boot=200, seed=42)
        self.assertEqual(r1, r2)


# ------------------------------------------------------------- ollama availability
class TestOllamaAvailable(unittest.TestCase):
    def test_returns_bool(self) -> None:
        # just check it doesn't crash and returns a bool (may be True or False)
        result = ollama_available(host="http://localhost:11434", model="deepseek-r1:7b")
        self.assertIsInstance(result, bool)

    def test_bad_host_returns_false(self) -> None:
        self.assertFalse(ollama_available(host="http://127.0.0.1:59999", model="deepseek-r1:7b"))


if __name__ == "__main__":
    unittest.main()
