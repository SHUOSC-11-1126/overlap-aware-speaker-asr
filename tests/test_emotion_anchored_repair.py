"""Unit tests for emotion-anchored ASR repair (issue #833).

Pure logic tested offline with injected fake LLM + fake emotion reader (no ollama, no Whisper),
mirroring test_llm_asr_critic / test_semantic_emotion_tax. Must pass under `unittest discover`.
"""
from __future__ import annotations

import math
import unittest

from src import emotion_anchored_repair as ear


class _FakeRepairLLM:
    """Returns a fixed corrected sentence via the `修正：` marker for any prompt; records calls."""

    def __init__(self, corrected="纠正后的句子"):
        self.corrected = corrected
        self.calls = 0

    def __call__(self, prompt: str) -> str:
        self.calls += 1
        return f"<think>reasoning…</think>\n修正：{self.corrected}"


class _EmptyLLM:
    def __call__(self, prompt: str) -> str:
        return "<think>…</think>\n"  # no usable answer -> fallback path


class _FakeReader:
    """Stand-in for semantic_emotion_tax.LlmEmotionReader.read()."""

    def __init__(self, reading):
        self._reading = reading
        self.calls = 0

    def read(self, text):
        self.calls += 1
        return self._reading


class TestAnchoredPrompt(unittest.TestCase):
    def test_prompt_embeds_transcript_and_stance(self):
        p = ear.build_anchored_repair_prompt("我反对这个观点", stance="oppose", valence=-0.8)
        self.assertIn("我反对这个观点", p)            # transcript present
        self.assertIn("反对", p)                       # stance rendered in Chinese (oppose->反对)
        self.assertIn("修正", p)                       # answer marker requested
        # must instruct preservation of the detected stance (the anchor)
        self.assertTrue(("立场" in p) or ("保持" in p))

    def test_prompt_stance_mapping(self):
        self.assertIn("支持", ear.build_anchored_repair_prompt("x", "support", 0.7))
        self.assertIn("中立", ear.build_anchored_repair_prompt("x", "neutral", 0.0))


class TestAnchoredRepair(unittest.TestCase):
    def test_reads_stance_then_repairs(self):
        reader = _FakeReader({"valence": -0.8, "arousal": 0.5, "stance": "oppose"})
        llm = _FakeRepairLLM("我坚决反对这个观点")
        repaired, reading = ear.anchored_repair("我反 对 这个观点", llm, reader)
        self.assertEqual(repaired, "我坚决反对这个观点")
        self.assertEqual(reading["stance"], "oppose")
        self.assertEqual(reader.calls, 1)   # exactly one emotion read
        self.assertEqual(llm.calls, 1)      # exactly one repair call

    def test_fallback_keeps_original_when_llm_empty(self):
        reader = _FakeReader({"valence": 0.0, "arousal": 0.0, "stance": "neutral"})
        repaired, _ = ear.anchored_repair("原始句子", _EmptyLLM(), reader)
        self.assertEqual(repaired, "原始句子")

    def test_handles_unreadable_stance(self):
        # reader returns None (LLM couldn't parse) -> defaults to neutral, still repairs
        reader = _FakeReader(None)
        repaired, reading = ear.anchored_repair("某句子", _FakeRepairLLM("修好的句子"), reader)
        self.assertEqual(repaired, "修好的句子")
        self.assertIsNone(reading)


class TestSummarizeRepair(unittest.TestCase):
    def _rows(self):
        # 2 clean (cer_before<0.30) + 2 hallucinated (cer_before>1.0)
        return [
            # clean: naive DAMAGES (0.10->0.55), anchored barely (0.10->0.15)
            {"cer_before": 0.10, "cer_naive": 0.55, "cer_anchored": 0.15,
             "max_compression_ratio": 1.0, "hallucinated": 0,
             "sem_dist_naive": 0.9, "sem_dist_anchored": 0.2},
            {"cer_before": 0.20, "cer_naive": 0.40, "cer_anchored": 0.22,
             "max_compression_ratio": 1.2, "hallucinated": 0,
             "sem_dist_naive": 0.7, "sem_dist_anchored": 0.1},
            # hallucinated: both help (2.0->1.0)
            {"cer_before": 2.0, "cer_naive": 1.0, "cer_anchored": 1.1,
             "max_compression_ratio": 3.5, "hallucinated": 1,
             "sem_dist_naive": 0.5, "sem_dist_anchored": 0.4},
            {"cer_before": 1.8, "cer_naive": 1.2, "cer_anchored": 1.0,
             "max_compression_ratio": 3.0, "hallucinated": 1,
             "sem_dist_naive": 0.6, "sem_dist_anchored": 0.3},
        ]

    def test_clean_damage_and_h1(self):
        s = ear.summarize_repair(self._rows())
        # clean delta = mean(before - after); negative = damage. anchored should be less negative.
        # naive clean: mean((0.10-0.55),(0.20-0.40)) = mean(-0.45,-0.20) = -0.325
        # anchored clean: mean((0.10-0.15),(0.20-0.22)) = mean(-0.05,-0.02) = -0.035
        self.assertAlmostEqual(s["clean_delta_naive"], -0.325, places=3)
        self.assertAlmostEqual(s["clean_delta_anchored"], -0.035, places=3)
        self.assertTrue(s["H1_anchored_less_clean_damage"])

    def test_pooled_delta_and_h2(self):
        s = ear.summarize_repair(self._rows())
        # pooled naive delta = mean(-0.45,-0.20,1.0,0.6)=0.2375 ; anchored=mean(-0.05,-0.02,0.9,0.8)=0.4075
        self.assertAlmostEqual(s["pooled_delta_naive"], 0.2375, places=3)
        self.assertAlmostEqual(s["pooled_delta_anchored"], 0.4075, places=3)
        self.assertTrue(s["H2_anchored_not_worse"])

    def test_stance_preservation_h3(self):
        s = ear.summarize_repair(self._rows())
        self.assertLess(s["mean_sem_dist_anchored"], s["mean_sem_dist_naive"])
        self.assertTrue(s["H3_anchored_preserves_stance"])

    def test_cr_gated_anchored(self):
        s = ear.summarize_repair(self._rows())
        # gate: apply anchored only when CR>2.4 (the 2 hallucinated), else keep cer_before.
        # mean(0.10, 0.20, 1.1, 1.0) = 0.6
        self.assertAlmostEqual(s["mean_cer_cr_gated_anchored"], 0.6, places=6)

    def test_cost_accounting(self):
        s = ear.summarize_repair(self._rows())
        # naive=1 call/case; anchored=2 (read+repair); cr_gated_anchored=1 read + repair only when gated
        self.assertEqual(s["llm_calls_naive"], 4)
        self.assertEqual(s["llm_calls_anchored"], 8)
        self.assertEqual(s["llm_calls_cr_gated_anchored"], 4 + 2)  # 4 reads + 2 gated repairs

    def test_empty_rows_safe(self):
        s = ear.summarize_repair([])
        self.assertEqual(s["n"], 0)
        self.assertTrue(math.isnan(s["pooled_delta_naive"]))


if __name__ == "__main__":
    unittest.main()
