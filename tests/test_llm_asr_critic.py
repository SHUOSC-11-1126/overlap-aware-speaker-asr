"""Tests for the prosody-grounded LLM x ASR critic (experimental/frontier).

Pin the PURE, model-free logic with an INJECTED fake LLM (so tests run offline without ollama):
think-stripping, SCORE / repair parsing, the judge and repair entry points, the over-correction guard,
and the QE-vs-CER correlation summary. The real deepseek-r1/ollama backend is exercised only by the
driver, never in unit tests.
"""
from __future__ import annotations

import unittest

from src.llm_asr_critic import (
    judge_quality,
    parse_score,
    repair_transcript,
    strip_think,
    summarize_critic,
)


def fake_llm(response: str):
    """Return an LLMFn that always replies with `response` (ignores the prompt)."""
    return lambda prompt: response


class TestStripThink(unittest.TestCase):
    def test_removes_think_block(self) -> None:
        self.assertEqual(strip_think("<think>reasoning here</think>\nSCORE: 0.9").strip(), "SCORE: 0.9")

    def test_no_think_passthrough(self) -> None:
        self.assertEqual(strip_think("SCORE: 0.5"), "SCORE: 0.5")

    def test_unclosed_think_is_dropped(self) -> None:
        # a truncated/unclosed think block should not leak reasoning into the answer
        self.assertEqual(strip_think("<think>still thinking and cut off").strip(), "")


class TestParseScore(unittest.TestCase):
    def test_basic(self) -> None:
        self.assertAlmostEqual(parse_score("SCORE: 0.95"), 0.95)

    def test_in_prose(self) -> None:
        self.assertAlmostEqual(parse_score("最终评分如下\nSCORE: 0.2"), 0.2)

    def test_clamped(self) -> None:
        self.assertEqual(parse_score("SCORE: 1.5"), 1.0)
        self.assertEqual(parse_score("SCORE: -3"), 0.0)

    def test_missing_returns_none(self) -> None:
        self.assertIsNone(parse_score("no score here"))


class TestJudgeQuality(unittest.TestCase):
    def test_parses_injected_score(self) -> None:
        llm = fake_llm("<think>looks fine</think>\nSCORE: 0.9")
        self.assertAlmostEqual(judge_quality("我认为这是对的", llm), 0.9)

    def test_unparseable_returns_nan(self) -> None:
        import math
        self.assertTrue(math.isnan(judge_quality("x", fake_llm("garbage"))))


class TestRepair(unittest.TestCase):
    def test_repair_extracts_corrected_line(self) -> None:
        llm = fake_llm("<think>fixing</think>\n修正：我们今天讨论人工智能")
        out = repair_transcript("我门今天讨论人工只能", llm)
        self.assertEqual(out, "我们今天讨论人工智能")

    def test_repair_falls_back_to_input_when_empty(self) -> None:
        # over-correction guard: if the model returns nothing usable, keep the original
        out = repair_transcript("原始文本", fake_llm("<think>...</think>\n"))
        self.assertEqual(out, "原始文本")

    def test_repair_without_marker_uses_final_text(self) -> None:
        out = repair_transcript("坏文本", fake_llm("好的文本"))
        self.assertEqual(out, "好的文本")


class TestSummarizeCritic(unittest.TestCase):
    def _rows(self):
        # judge score should track quality: high CER -> low score (negative corr). CR rises with CER
        # too (a competing cheap signal).
        return [
            {"cer": 0.05, "judge_score": 0.95, "cer_before": 0.05, "cer_after": 0.05, "hallucinated": 0, "max_compression_ratio": 1.0},
            {"cer": 0.10, "judge_score": 0.90, "cer_before": 0.10, "cer_after": 0.08, "hallucinated": 0, "max_compression_ratio": 1.2},
            {"cer": 1.50, "judge_score": 0.10, "cer_before": 1.50, "cer_after": 0.60, "hallucinated": 1, "max_compression_ratio": 2.8},
            {"cer": 2.00, "judge_score": 0.05, "cer_before": 2.00, "cer_after": 0.90, "hallucinated": 1, "max_compression_ratio": 3.5},
        ]

    def test_qe_correlation_negative(self) -> None:
        s = summarize_critic(self._rows())
        self.assertLess(s["pearson_judge_cer"], -0.8)  # low score <-> high CER

    def test_cr_qe_signal_present(self) -> None:
        s = summarize_critic(self._rows())
        self.assertGreater(s["pearson_cr_cer"], 0.8)   # CR also tracks CER (the competing signal)
        self.assertIn(s["qe_winner"], ("compression_ratio", "llm_judge"))

    def test_repair_helps_hallucinated(self) -> None:
        s = summarize_critic(self._rows())
        self.assertGreater(s["mean_cer_reduction_hallucinated"], 0.0)

    def test_overcorrection_check_on_clean(self) -> None:
        s = summarize_critic(self._rows())
        # clean cases should not be worsened (reduction >= ~0)
        self.assertGreaterEqual(s["mean_cer_reduction_clean"], -0.05)

    def test_keys_present(self) -> None:
        s = summarize_critic(self._rows())
        for k in ("n", "pearson_judge_cer", "pearson_cr_cer", "qe_winner",
                  "mean_cer_reduction_hallucinated", "mean_cer_reduction_clean", "n_hallucinated",
                  "mean_cer_after_naive_repair", "mean_cer_after_cr_gated", "mean_cer_after_judge_gated"):
            self.assertIn(k, s)


if __name__ == "__main__":
    unittest.main()
