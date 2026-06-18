"""Unit tests for the Semantic Emotion Tax frontier module (issue #831).

All pure logic is tested WITHOUT ollama/Whisper/librosa: the LLM is dependency-injected as a
fake callable, exactly as src/llm_asr_critic.py is tested. These tests must pass under the
harness `unittest discover` gate offline.
"""
from __future__ import annotations

import math
import unittest

from src import semantic_emotion_tax as set_mod


class TestParseLlmEmotion(unittest.TestCase):
    def test_parses_deepseek_think_plus_fence(self):
        # The real deepseek-r1 shape: a <think> trace, then a ```json fenced object.
        raw = (
            "<think>\nThe speaker strongly opposes... valence near -1, arousal moderate.\n</think>\n\n"
            '```json\n{"valence": -1, "arousal": 0.3, "stance": "oppose"}\n```'
        )
        out = set_mod.parse_llm_emotion(raw)
        self.assertIsNotNone(out)
        self.assertAlmostEqual(out["valence"], -1.0)
        self.assertAlmostEqual(out["arousal"], 0.3)
        self.assertEqual(out["stance"], "oppose")

    def test_parses_bare_trailing_object(self):
        raw = 'Here is my answer: {"valence": 0.5, "arousal": 0.8, "stance": "support"} done'
        out = set_mod.parse_llm_emotion(raw)
        self.assertIsNotNone(out)
        self.assertAlmostEqual(out["valence"], 0.5)
        self.assertEqual(out["stance"], "support")

    def test_takes_final_object_after_think(self):
        # A stray object inside <think> must be ignored in favour of the post-think answer.
        raw = (
            '<think>maybe {"valence": 0.9, "arousal": 0.9, "stance": "support"} or not</think>'
            '{"valence": -0.5, "arousal": 0.2, "stance": "oppose"}'
        )
        out = set_mod.parse_llm_emotion(raw)
        self.assertEqual(out["stance"], "oppose")
        self.assertAlmostEqual(out["valence"], -0.5)

    def test_clamps_out_of_range(self):
        raw = '{"valence": 5, "arousal": -0.4, "stance": "oppose"}'
        out = set_mod.parse_llm_emotion(raw)
        self.assertEqual(out["valence"], 1.0)   # clamped to [-1, 1]
        self.assertEqual(out["arousal"], 0.0)   # clamped to [0, 1]

    def test_unknown_stance_becomes_neutral(self):
        raw = '{"valence": 0.0, "arousal": 0.1, "stance": "furious"}'
        out = set_mod.parse_llm_emotion(raw)
        self.assertEqual(out["stance"], "neutral")

    def test_garbage_returns_none(self):
        self.assertIsNone(set_mod.parse_llm_emotion("no json here at all"))
        self.assertIsNone(set_mod.parse_llm_emotion(""))
        self.assertIsNone(set_mod.parse_llm_emotion(None))

    def test_non_numeric_fields_return_none(self):
        # An object with no emotion keys is not a valid reading.
        self.assertIsNone(set_mod.parse_llm_emotion('{"foo": 1, "bar": 2}'))


class TestDegeneracyAndCoverage(unittest.TestCase):
    def test_is_degenerate(self):
        self.assertTrue(set_mod.is_degenerate(None))
        self.assertTrue(set_mod.is_degenerate({"valence": 0.0, "arousal": 0.0, "stance": "neutral"}))
        self.assertFalse(set_mod.is_degenerate({"valence": -0.5, "arousal": 0.0, "stance": "neutral"}))
        self.assertFalse(set_mod.is_degenerate({"valence": 0.0, "arousal": 0.0, "stance": "oppose"}))

    def test_coverage_rate(self):
        readings = [
            {"valence": -0.5, "arousal": 0.3, "stance": "oppose"},  # signal
            None,                                                    # degenerate
            {"valence": 0.0, "arousal": 0.0, "stance": "neutral"},   # degenerate
            {"valence": 0.7, "arousal": 0.6, "stance": "support"},   # signal
        ]
        self.assertAlmostEqual(set_mod.coverage_rate(readings), 0.5)
        self.assertEqual(set_mod.coverage_rate([]), 0.0)


class TestSemanticDistance(unittest.TestCase):
    def test_distance_known(self):
        ref = {"valence": 1.0, "arousal": 0.5, "stance": "support"}
        hyp = {"valence": -1.0, "arousal": 0.5, "stance": "oppose"}
        d = set_mod.semantic_distance(ref, hyp)
        self.assertAlmostEqual(d["valence_dist"], 2.0)
        self.assertAlmostEqual(d["arousal_dist"], 0.0)
        self.assertEqual(d["stance_changed"], 1.0)
        self.assertAlmostEqual(d["combined"], 2.0)

    def test_distance_identity_is_zero(self):
        r = {"valence": 0.3, "arousal": 0.4, "stance": "neutral"}
        d = set_mod.semantic_distance(r, dict(r))
        self.assertAlmostEqual(d["combined"], 0.0)
        self.assertEqual(d["stance_changed"], 0.0)

    def test_distance_with_none_is_nan(self):
        d = set_mod.semantic_distance(None, {"valence": 0.1, "arousal": 0.1, "stance": "neutral"})
        self.assertTrue(math.isnan(d["combined"]))


class TestBenefitAndAggregate(unittest.TestCase):
    def test_semantic_benefit_sign(self):
        # separation lowers distance to clean text => positive benefit
        self.assertGreater(set_mod.semantic_benefit(0.8, 0.2), 0)
        self.assertLess(set_mod.semantic_benefit(0.1, 0.5), 0)

    def test_aggregate_detects_crossover(self):
        rows = [
            {"overlap_ratio": 0.0, "semantic_benefit": -0.2, "d_sem_mixed": 0.1, "d_sem_sep": 0.3},
            {"overlap_ratio": 0.0, "semantic_benefit": -0.1, "d_sem_mixed": 0.1, "d_sem_sep": 0.2},
            {"overlap_ratio": 0.8, "semantic_benefit": 0.3, "d_sem_mixed": 0.5, "d_sem_sep": 0.2},
            {"overlap_ratio": 0.8, "semantic_benefit": 0.5, "d_sem_mixed": 0.6, "d_sem_sep": 0.1},
        ]
        agg = set_mod.aggregate_tax(rows)
        self.assertTrue(agg["crossover_detected"])
        by = {r["overlap_ratio"]: r for r in agg["by_overlap"]}
        self.assertAlmostEqual(by[0.0]["mean_semantic_benefit"], -0.15)
        self.assertAlmostEqual(by[0.8]["mean_semantic_benefit"], 0.4)

    def test_aggregate_no_crossover_when_all_positive(self):
        rows = [
            {"overlap_ratio": 0.1, "semantic_benefit": 0.2, "d_sem_mixed": 0.4, "d_sem_sep": 0.2},
            {"overlap_ratio": 0.8, "semantic_benefit": 0.3, "d_sem_mixed": 0.6, "d_sem_sep": 0.3},
        ]
        self.assertFalse(set_mod.aggregate_tax(rows)["crossover_detected"])

    def test_aggregate_skips_nan_rows(self):
        # rows whose benefit is NaN (unparseable reading) must not crash aggregation
        rows = [
            {"overlap_ratio": 0.1, "semantic_benefit": float("nan"), "d_sem_mixed": float("nan"), "d_sem_sep": 0.2},
            {"overlap_ratio": 0.1, "semantic_benefit": 0.2, "d_sem_mixed": 0.4, "d_sem_sep": 0.2},
        ]
        agg = set_mod.aggregate_tax(rows)
        by = {r["overlap_ratio"]: r for r in agg["by_overlap"]}
        self.assertAlmostEqual(by[0.1]["mean_semantic_benefit"], 0.2)  # NaN ignored, n_valid=1


class TestCorrelate(unittest.TestCase):
    def test_perfect_positive(self):
        out = set_mod.correlate([1.0, 2.0, 3.0, 4.0], [2.0, 4.0, 6.0, 8.0])
        self.assertAlmostEqual(out["pearson"], 1.0, places=5)
        self.assertAlmostEqual(out["spearman"], 1.0, places=5)
        self.assertEqual(out["n"], 4)

    def test_constant_is_nan_safe(self):
        out = set_mod.correlate([1.0, 1.0, 1.0], [1.0, 2.0, 3.0])
        self.assertTrue(math.isnan(out["pearson"]))

    def test_drops_nan_pairs(self):
        out = set_mod.correlate([1.0, float("nan"), 3.0, 4.0], [2.0, 9.0, 6.0, 8.0])
        # the NaN pair is dropped, remaining (1,2),(3,6),(4,8) are perfectly correlated
        self.assertAlmostEqual(out["pearson"], 1.0, places=5)
        self.assertEqual(out["n"], 3)


class _FakeLLM:
    """Deterministic fake LLM: returns a canned JSON for a known phrase, neutral otherwise.
    Records call count to prove caching."""

    def __init__(self):
        self.calls = 0

    def __call__(self, prompt: str) -> str:
        self.calls += 1
        if "反对" in prompt:
            return '<think>opposes</think>```json\n{"valence": -0.8, "arousal": 0.4, "stance": "oppose"}\n```'
        return '{"valence": 0.0, "arousal": 0.0, "stance": "neutral"}'


class TestLlmEmotionReader(unittest.TestCase):
    def test_reads_and_parses(self):
        reader = set_mod.LlmEmotionReader(_FakeLLM())
        out = reader.read("我坚决反对这个观点")
        self.assertEqual(out["stance"], "oppose")
        self.assertAlmostEqual(out["valence"], -0.8)

    def test_caches_by_text(self):
        fake = _FakeLLM()
        reader = set_mod.LlmEmotionReader(fake)
        reader.read("我坚决反对这个观点")
        reader.read("我坚决反对这个观点")  # identical -> served from cache
        self.assertEqual(fake.calls, 1)

    def test_empty_text_returns_none_without_calling(self):
        fake = _FakeLLM()
        reader = set_mod.LlmEmotionReader(fake)
        self.assertIsNone(reader.read(""))
        self.assertIsNone(reader.read("   "))
        self.assertEqual(fake.calls, 0)


if __name__ == "__main__":
    unittest.main()
