"""Unit tests for the frontier capstone hero figure (issue #840)."""
from __future__ import annotations

import unittest

from src import frontier_capstone_figure as fcf


class TestExtractHeadlines(unittest.TestCase):
    def _summaries(self):
        return {
            "semantic_emotion_tax": {"H1_coverage": {"llm_coverage_rate": 0.70, "lexical_firing_rate": 0.10}},
            "emotion_anchored_repair": {"mean_cer_before": 0.92, "mean_cer_naive": 1.08, "mean_cer_anchored": 1.12},
            "emotion_modality_fusion": {"by_target": {
                "acoustic_emotion_damage": {"fused_r2": 0.02, "best_single_r2": 0.11},
                "semantic_emotion_damage": {"fused_r2": 0.16, "best_single_r2": 0.10}}},
            "noise_robust_router": {"pooled": {"mean_cer_mixed": 1.21, "mean_cer_speaker_gate": 1.53,
                                               "mean_cer_router": 0.78, "mean_cer_oracle": 0.74}},
            "llm_speaker_attribution": {"llm_attribution_accuracy": 0.08,
                                        "calibrated_attribution_accuracy": 0.92},
        }

    def test_extracts_all_five(self):
        h = fcf.extract_headlines(self._summaries())
        self.assertEqual(set(h), set(fcf.RESULTS))
        self.assertAlmostEqual(h["semantic_emotion_tax"]["LLM"], 0.70)
        self.assertAlmostEqual(h["semantic_emotion_tax"]["lexicon"], 0.10)
        self.assertAlmostEqual(h["noise_robust_router"]["router"], 0.78)
        self.assertAlmostEqual(h["llm_speaker_attribution"]["calibrated"], 0.92)

    def test_missing_experiment_skipped(self):
        h = fcf.extract_headlines({"semantic_emotion_tax": self._summaries()["semantic_emotion_tax"]})
        self.assertIn("semantic_emotion_tax", h)
        self.assertNotIn("noise_robust_router", h)

    def test_empty_safe(self):
        self.assertEqual(fcf.extract_headlines({}), {})


if __name__ == "__main__":
    unittest.main()
