"""Unit tests for LLM speaker-attribution repair (issue #838).

Pure attribution/eval logic tested offline on synthetic rows (no ollama/Whisper). Must pass under
`unittest discover`.
"""
from __future__ import annotations

import math
import unittest

from src import llm_speaker_attribution as lsa


class TestAssignByValence(unittest.TestCase):
    def test_lower_valence_is_con(self):
        # con opposes -> more negative valence; pro supports -> more positive
        self.assertEqual(lsa.assign_by_valence({"valence": -0.6}, {"valence": 0.4}), "a")  # a=con
        self.assertEqual(lsa.assign_by_valence({"valence": 0.5}, {"valence": -0.2}), "b")  # b=con

    def test_abstains_on_tie_or_missing(self):
        self.assertIsNone(lsa.assign_by_valence({"valence": 0.3}, {"valence": 0.3}))
        self.assertIsNone(lsa.assign_by_valence(None, {"valence": 0.1}))
        self.assertIsNone(lsa.assign_by_valence({"valence": 0.1}, None))


class TestRankAuc(unittest.TestCase):
    def test_perfect_separation(self):
        # pro valences all above con valences -> AUC 1.0
        self.assertAlmostEqual(lsa.rank_auc(pos=[0.5, 0.6, 0.7], neg=[-0.1, 0.0, 0.1]), 1.0)

    def test_no_separation(self):
        auc = lsa.rank_auc(pos=[0.1, 0.2], neg=[0.1, 0.2])
        self.assertAlmostEqual(auc, 0.5, places=5)

    def test_reversed(self):
        self.assertAlmostEqual(lsa.rank_auc(pos=[-1.0, -0.5], neg=[0.5, 1.0]), 0.0)


class TestEvaluate(unittest.TestCase):
    def _rows_separable(self):
        # con tracks negative valence, pro positive -> valence discriminates perfectly
        return [
            {"sample_id": f"s{i}", "con_text": "反对", "pro_text": "支持",
             "con_valence": -0.5 - 0.01 * i, "pro_valence": 0.5 + 0.01 * i,
             "con_stance": "oppose", "pro_stance": "support",
             "ref_con": "我反对这个观点完全错误", "ref_pro": "我支持这个观点非常正确"}
            for i in range(10)
        ]

    def _rows_nonseparable(self):
        # both read same valence -> no signal
        return [
            {"sample_id": f"s{i}", "con_text": "甲", "pro_text": "乙",
             "con_valence": 0.2, "pro_valence": 0.2,
             "con_stance": "support", "pro_stance": "support",
             "ref_con": "甲方观点", "ref_pro": "乙方观点"}
            for i in range(10)
        ]

    def test_separable_supports_h1_h2(self):
        out = lsa.evaluate(self._rows_separable(), swap_rate=0.5)
        self.assertGreater(out["valence_auc"], 0.9)
        self.assertGreater(out["llm_attribution_accuracy"], 0.9)
        self.assertTrue(out["H1_valence_discriminates"])
        self.assertTrue(out["H2_llm_beats_chance"])

    def test_nonseparable_is_bounding_negative(self):
        out = lsa.evaluate(self._rows_nonseparable(), swap_rate=0.5)
        self.assertAlmostEqual(out["valence_auc"], 0.5, places=5)
        self.assertFalse(out["H1_valence_discriminates"])
        # abstains on ties -> accuracy is the abstain fallback, not > chance by signal
        self.assertFalse(out["H2_llm_beats_chance"])

    def test_repair_vs_swapping_separator(self):
        out = lsa.evaluate(self._rows_separable(), swap_rate=0.5)
        # a separator that swaps 50% has 0.5 accuracy; perfect valence repair beats it
        self.assertAlmostEqual(out["raw_accuracy_at_swap_rate"], 0.5, places=5)
        self.assertGreater(out["llm_attribution_accuracy"], out["raw_accuracy_at_swap_rate"])
        self.assertIn("attributed_cer_oracle", out)
        self.assertIn("attributed_cer_llm", out)

    def test_empty_safe(self):
        out = lsa.evaluate([], swap_rate=0.5)
        self.assertEqual(out["n"], 0)
        self.assertTrue(math.isnan(out["valence_auc"]))

    def test_reversed_direction_calibrated_recovers(self):
        # con tracks read MORE POSITIVE than pro (counterintuitive — like the real #838 data):
        # the naive prior is backwards, but the SIGNAL is strong, so a sign-calibrated rule recovers it.
        rows = [{"sample_id": f"s{i}", "con_text": "反对", "pro_text": "支持",
                 "con_valence": 0.5 + 0.01 * i, "pro_valence": -0.5 - 0.01 * i,
                 "con_stance": "support", "pro_stance": "support",
                 "ref_con": "我反对这个完全错误", "ref_pro": "我支持这个非常正确"}
                for i in range(10)]
        out = lsa.evaluate(rows, swap_rate=0.5)
        self.assertLess(out["llm_attribution_accuracy"], 0.1)              # naive rule backwards
        self.assertGreater(out["calibrated_attribution_accuracy"], 0.9)   # sign-calibrated recovers
        self.assertEqual(out["valence_direction"], "con_higher_valence")
        self.assertTrue(out["H1_valence_discriminates"])                  # signal exists (AUC far from 0.5)
        self.assertFalse(out["H2_llm_beats_chance"])                      # naive fails reference-free
        self.assertTrue(out["H2b_calibrated_beats_chance"])              # calibrated succeeds


if __name__ == "__main__":
    unittest.main()
