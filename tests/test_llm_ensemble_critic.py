"""Tests for the RQ41 multi-call LLM ensemble critic (experimental/frontier).

Pin the PURE, model-free logic with an INJECTED fake LLM (so tests run offline without
ollama): think-stripping, hallucination/confidence parsing, majority vote, mean
confidence aggregation, n-gram KL divergence, cache key/save/load, threshold
calibration, and bootstrap CIs. The real deepseek-r1/ollama backend is exercised only
by the analysis driver, never in unit tests.
"""
from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.llm_ensemble_critic import (
    aggregate_ensemble,
    bootstrap_ci,
    build_hallucination_prompt,
    cache_key,
    calibrate_threshold,
    ceiling_analysis,
    char_ngrams,
    flag_at,
    kl_divergence,
    load_cache,
    majority_vote,
    mean_confidence,
    ngram_distribution,
    ngram_kl,
    parse_hallucination,
    save_cache,
    strip_think,
    transcript_hash,
    yes_count,
    ensemble_judge,
)


def fake_llm(response: str):
    """Return an LLMFn that always replies with `response` (ignores prompt/temperature)."""
    return lambda prompt, temperature=0.0: response


class TestStripThink(unittest.TestCase):
    def test_removes_think_block(self) -> None:
        self.assertEqual(
            strip_think("<think>reasoning here</think>\nHALLUCINATED: no").strip(),
            "HALLUCINATED: no")

    def test_no_think_passthrough(self) -> None:
        self.assertEqual(strip_think("HALLUCINATED: yes"), "HALLUCINATED: yes")

    def test_unclosed_think_is_dropped(self) -> None:
        self.assertEqual(strip_think("<think>still thinking and cut off").strip(), "")


class TestParseHallucination(unittest.TestCase):
    def test_yes_no(self) -> None:
        h, c = parse_hallucination("<think>looks bad</think>\nHALLUCINATED: yes\nCONFIDENCE: 0.8")
        self.assertTrue(h)
        self.assertAlmostEqual(c, 0.8)

    def test_no(self) -> None:
        h, c = parse_hallucination("HALLUCINATED: no\nCONFIDENCE: 0.9")
        self.assertFalse(h)
        self.assertAlmostEqual(c, 0.9)

    def test_chinese_yes_no(self) -> None:
        h, _ = parse_hallucination("HALLUCINATED: 是\nCONFIDENCE: 0.7")
        self.assertTrue(h)
        h, _ = parse_hallucination("HALLUCINATED: 否\nCONFIDENCE: 0.6")
        self.assertFalse(h)

    def test_confidence_clamped(self) -> None:
        _, c = parse_hallucination("HALLUCINATED: yes\nCONFIDENCE: 1.5")
        self.assertAlmostEqual(c, 1.0)
        _, c = parse_hallucination("HALLUCINATED: yes\nCONFIDENCE: -0.2")
        self.assertAlmostEqual(c, 0.0)

    def test_missing_returns_none(self) -> None:
        h, c = parse_hallucination("no verdict here")
        self.assertIsNone(h)
        self.assertIsNone(c)

    def test_in_prose(self) -> None:
        h, c = parse_hallucination("最终判断如下\nHALLUCINATED: yes\nCONFIDENCE: 0.55")
        self.assertTrue(h)
        self.assertAlmostEqual(c, 0.55)

    def test_case_insensitive(self) -> None:
        h, _ = parse_hallucination("hallucinated: YES\nconfidence: 0.5")
        self.assertTrue(h)


class TestMajorityVote(unittest.TestCase):
    def test_strict_majority_yes(self) -> None:
        self.assertTrue(majority_vote([True, True, True, False, False]))

    def test_strict_majority_no(self) -> None:
        self.assertFalse(majority_vote([True, True, False, False, False]))

    def test_tie_resolves_false(self) -> None:
        # 2-2 (ignoring None): not strictly more than half -> False
        self.assertFalse(majority_vote([True, True, False, False, None]))

    def test_all_none_returns_false(self) -> None:
        self.assertFalse(majority_vote([None, None, None]))

    def test_ignores_none(self) -> None:
        # 3 True, 1 False, 1 None -> True
        self.assertTrue(majority_vote([True, True, True, False, None]))


class TestConfidenceAggregation(unittest.TestCase):
    def test_mean_confidence(self) -> None:
        self.assertAlmostEqual(mean_confidence([0.8, 0.6, 0.4, 0.2, 0.0]), 0.4)

    def test_mean_confidence_ignores_none(self) -> None:
        self.assertAlmostEqual(mean_confidence([0.8, None, 0.4]), 0.6)

    def test_mean_confidence_all_none(self) -> None:
        self.assertAlmostEqual(mean_confidence([None, None]), 0.0)

    def test_yes_count(self) -> None:
        self.assertEqual(yes_count([True, True, False, None, True]), 3)


class TestAggregateEnsemble(unittest.TestCase):
    def _calls(self):
        return [
            {"temperature": 0.0, "hallucinated": True, "confidence": 0.8},
            {"temperature": 0.2, "hallucinated": True, "confidence": 0.7},
            {"temperature": 0.4, "hallucinated": False, "confidence": 0.6},
            {"temperature": 0.6, "hallucinated": True, "confidence": 0.5},
            {"temperature": 0.8, "hallucinated": False, "confidence": 0.4},
        ]

    def test_majority_and_confidence(self) -> None:
        agg = aggregate_ensemble(self._calls())
        self.assertTrue(agg["hallucinated_majority"])  # 3 of 5 yes
        self.assertAlmostEqual(agg["mean_confidence"], 0.6)
        self.assertEqual(agg["yes_count"], 3)
        self.assertEqual(agg["n_calls"], 5)
        self.assertEqual(agg["n_parseable"], 5)
        self.assertAlmostEqual(agg["yes_vote_fraction"], 0.6)

    def test_no_majority(self) -> None:
        calls = [
            {"temperature": 0.0, "hallucinated": False, "confidence": 0.9},
            {"temperature": 0.2, "hallucinated": False, "confidence": 0.8},
            {"temperature": 0.4, "hallucinated": True, "confidence": 0.5},
            {"temperature": 0.6, "hallucinated": False, "confidence": 0.7},
            {"temperature": 0.8, "hallucinated": False, "confidence": 0.6},
        ]
        agg = aggregate_ensemble(calls)
        self.assertFalse(agg["hallucinated_majority"])
        self.assertEqual(agg["yes_count"], 1)


class TestNgramKL(unittest.TestCase):
    def test_char_ngrams(self) -> None:
        self.assertEqual(char_ngrams("abc", 2), ["ab", "bc"])
        self.assertEqual(char_ngrams("a", 2), ["a"])
        self.assertEqual(char_ngrams("", 2), [])

    def test_ngram_distribution_sums_to_one(self) -> None:
        d = ngram_distribution("abcabc", 2)
        self.assertAlmostEqual(sum(d.values()), 1.0)
        self.assertAlmostEqual(d["ab"], 2 / 5)

    def test_kl_identical_is_zero(self) -> None:
        p = ngram_distribution("abcabc", 2)
        self.assertAlmostEqual(kl_divergence(p, p), 0.0, places=5)

    def test_kl_positive_for_different(self) -> None:
        p = ngram_distribution("aaaa", 2)
        q = ngram_distribution("abcd", 2)
        self.assertGreater(kl_divergence(p, q), 0.0)

    def test_kl_empty_p_is_zero(self) -> None:
        self.assertEqual(kl_divergence({}, {"a": 1.0}), 0.0)

    def test_ngram_kl_empty_sep(self) -> None:
        self.assertEqual(ngram_kl("", "abc"), 0.0)

    def test_ngram_kl_empty_mix_sentinel(self) -> None:
        # non-empty sep but empty mix -> entirely novel -> large sentinel
        self.assertEqual(ngram_kl("abc", ""), 100.0)

    def test_ngram_kl_near_duplicate_is_lower_than_diverse(self) -> None:
        # Mode S profile: sep is a near-duplicate of mix -> lower KL than diverse
        # hallucination (sep totally different from mix). Use long enough texts for
        # trigram overlap to be meaningful.
        sep_dup = "我说一下那些男生后等我们男生后这时每次消息我都是不算很高的" * 3
        mix_dup = "我说一下那种南方户的我们南方户这时每次消息我都是不算很高的" * 3
        sep_div = "龫龍來不战但是他們也是見我們拿天出functional划掉甜頭" * 3
        mix_div = "我这边儿也了解你们大体的一些基本情况零零幺商场经理" * 3
        kl_dup = ngram_kl(sep_dup, mix_dup, n=3)
        kl_div = ngram_kl(sep_div, mix_div, n=3)
        self.assertGreater(kl_dup, 0.0)
        # near-duplicate should have lower KL than diverse hallucination
        self.assertLess(kl_dup, kl_div)


class TestCache(unittest.TestCase):
    def test_transcript_hash_stable(self) -> None:
        self.assertEqual(transcript_hash("hello"), transcript_hash("hello"))
        self.assertNotEqual(transcript_hash("hello"), transcript_hash("world"))

    def test_cache_key_includes_temperature(self) -> None:
        k0 = cache_key("hello", 0.0)
        k8 = cache_key("hello", 0.8)
        self.assertNotEqual(k0, k8)
        self.assertIn("t0.0", k0)
        self.assertIn("t0.8", k8)

    def test_save_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "cache.json"
            cache = {"key1": {"hallucinated": True, "confidence": 0.8, "response": "x"}}
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


class TestEnsembleJudge(unittest.TestCase):
    def test_uses_fake_llm(self) -> None:
        llm = fake_llm("<think>x</think>\nHALLUCINATED: yes\nCONFIDENCE: 0.7")
        agg = ensemble_judge("some text", llm, temperatures=[0.0, 0.2])
        self.assertTrue(agg["hallucinated_majority"])
        self.assertAlmostEqual(agg["mean_confidence"], 0.7)
        self.assertEqual(agg["n_calls"], 2)
        self.assertEqual(agg["n_new_calls"], 2)

    def test_cache_hit_skips_llm(self) -> None:
        call_count = [0]

        def counting_llm(prompt, temperature=0.0):
            call_count[0] += 1
            return "HALLUCINATED: no\nCONFIDENCE: 0.9"

        cache = {cache_key("text", 0.0): {"hallucinated": False, "confidence": 0.9, "response": "cached"}}
        agg = ensemble_judge("text", counting_llm, temperatures=[0.0, 0.2], cache=cache)
        # 0.0 is cached, 0.2 is new -> 1 live call
        self.assertEqual(call_count[0], 1)
        self.assertEqual(agg["n_cache_hits"], 1)
        self.assertEqual(agg["n_new_calls"], 1)

    def test_empty_transcript_short_circuit(self) -> None:
        call_count = [0]

        def counting_llm(prompt, temperature=0.0):
            call_count[0] += 1
            return "HALLUCINATED: no"

        agg = ensemble_judge("", counting_llm, temperatures=[0.0, 0.2, 0.4])
        self.assertEqual(call_count[0], 0)  # no LLM calls for empty text
        self.assertFalse(agg["hallucinated_majority"])
        self.assertTrue(agg["empty_short_circuit"])

    def test_mixed_parseable_and_none(self) -> None:
        # some calls unparseable -> majority uses only parseable
        responses = [
            "HALLUCINATED: yes\nCONFIDENCE: 0.8",   # t=0.0
            "garbage no verdict",                     # t=0.2 -> None
            "HALLUCINATED: yes\nCONFIDENCE: 0.6",   # t=0.4
        ]
        llm = make_sequence_llm(responses)
        agg = ensemble_judge("text", llm, temperatures=[0.0, 0.2, 0.4])
        self.assertEqual(agg["n_parseable"], 2)
        self.assertTrue(agg["hallucinated_majority"])  # 2 of 2 parseable are yes


def make_sequence_llm(responses: list[str]):
    """Return an LLMFn that returns each response in turn (ignores temperature)."""
    it = iter(responses)
    return lambda prompt, temperature=0.0: next(it)


class TestCalibration(unittest.TestCase):
    def test_calibrate_finds_90pct_spec(self) -> None:
        # 10 negatives with scores 0.0-0.9, 2 Mode S positives high, 5 all-halluc high
        neg = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        pos_ms = [1.0, 0.95]
        pos_ah = [1.0, 0.95, 0.9, 0.85, 0.8]
        op = calibrate_threshold(neg, pos_ms, pos_ah, target_spec=0.9)
        self.assertGreaterEqual(op["specificity"], 0.9 - 1e-9)
        # threshold >= 1.0 would give 100% spec but catch only Mode S at exactly 1.0
        # threshold 0.95 -> 1 FP (0.95? no, 0.9 < 0.95), spec=90%, catches both Mode S
        self.assertEqual(op["tp_mode_s"], 2)

    def test_flag_at(self) -> None:
        self.assertTrue(flag_at(0.8, 0.6))
        self.assertFalse(flag_at(0.4, 0.6))

    def test_no_threshold_meets_spec(self) -> None:
        # all negatives have score 1.0 -> cannot reach 90% spec without threshold > 1.0
        neg = [1.0, 1.0, 1.0]
        op = calibrate_threshold(neg, [1.0], [1.0], target_spec=0.9)
        # threshold > 1.0 -> 100% spec, 0% sensitivity
        self.assertAlmostEqual(op["specificity"], 1.0)
        self.assertAlmostEqual(op["sensitivity_mode_s"], 0.0)


class TestBootstrap(unittest.TestCase):
    def test_sensitivity_ci_bounds(self) -> None:
        # Use overlapping scores so the CI is non-degenerate (not all 1.0).
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


class TestCeilingAnalysis(unittest.TestCase):
    def test_relaxing_spec_increases_sensitivity(self) -> None:
        neg = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        pos_ms = [0.85, 0.95]
        ceil = ceiling_analysis(neg, pos_ms, [0.5, 0.9])
        # at 50% spec floor we can catch more Mode S than at 90%
        self.assertGreaterEqual(ceil[0]["max_sensitivity_mode_s"],
                                ceil[1]["max_sensitivity_mode_s"])


class TestPrompt(unittest.TestCase):
    def test_prompt_contains_transcript(self) -> None:
        p = build_hallucination_prompt("测试文本")
        self.assertIn("测试文本", p)
        self.assertIn("HALLUCINATED", p)
        self.assertIn("CONFIDENCE", p)


if __name__ == "__main__":
    unittest.main()
