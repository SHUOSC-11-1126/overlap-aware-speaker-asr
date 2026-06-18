"""Tests for objective-aware decoupled routing (experimental/frontier).

Pin the PURE routing logic: per-strategy (CER, emotion) outcomes, the coupling cost a single-switch
system pays, and the normalized joint-regret summary. No Whisper/librosa (per-condition CER and
emotion-distortion are passed in as records).
"""
from __future__ import annotations

import unittest

from src.objective_aware_routing import (
    coupling_cost,
    strategy_outcomes,
    summarize_routing,
)


def _rec(ov, cm, cs, em, es):
    # text_route is the ASR-optimal (argmin CER) choice; driver computes it (oracle text router).
    return {"overlap_ratio": ov, "cer_mixed": cm, "cer_sep": cs, "emo_mixed": em, "emo_sep": es,
            "text_route": "sep" if cs < cm else "mixed"}


class TestStrategyOutcomes(unittest.TestCase):
    def test_low_overlap_decoupled_beats_coupled_on_emotion(self) -> None:
        # text wants mixed (cer 0.2<0.5), emotion wants sep (0.1<0.3)
        out = strategy_outcomes(_rec(0.1, 0.2, 0.5, 0.3, 0.1))
        self.assertEqual(out["coupled"], (0.2, 0.3))     # one switch (mixed) -> mixed emotion
        self.assertEqual(out["decoupled"], (0.2, 0.1))   # text mixed, emotion always sep
        self.assertEqual(out["always_mixed"], (0.2, 0.3))
        self.assertEqual(out["always_sep"], (0.5, 0.1))
        self.assertEqual(out["oracle"], (0.2, 0.1))      # best per axis

    def test_high_overlap_coupled_equals_decoupled(self) -> None:
        # text wants sep (0.2<0.6); emotion also from sep -> coupling free
        out = strategy_outcomes(_rec(0.9, 0.6, 0.2, 0.4, 0.1))
        self.assertEqual(out["coupled"], (0.2, 0.1))
        self.assertEqual(out["decoupled"], (0.2, 0.1))


class TestCouplingCost(unittest.TestCase):
    def test_positive_when_text_route_is_mixed(self) -> None:
        # coupling forfeits emotion fidelity = emo[text_route] - emo_sep
        self.assertAlmostEqual(coupling_cost(_rec(0.1, 0.2, 0.5, 0.3, 0.1)), 0.2, places=6)

    def test_zero_when_text_route_is_sep(self) -> None:
        self.assertAlmostEqual(coupling_cost(_rec(0.9, 0.6, 0.2, 0.4, 0.1)), 0.0, places=6)


class TestSummarizeRouting(unittest.TestCase):
    def _records(self):
        return [
            _rec(0.1, 0.2, 0.5, 0.3, 0.1),  # low: text mixed, emotion wants sep
            _rec(0.3, 0.3, 0.6, 0.3, 0.1),  # mid: text mixed, emotion wants sep
            _rec(0.9, 0.6, 0.2, 0.4, 0.1),  # high: text sep, agree
        ]

    def test_decoupled_better_or_equal_emotion_than_coupled(self) -> None:
        s = summarize_routing(self._records())
        self.assertLessEqual(s["mean_emo_decoupled"], s["mean_emo_coupled"])
        # same text route -> identical CER
        self.assertAlmostEqual(s["mean_cer_decoupled"], s["mean_cer_coupled"], places=6)

    def test_coupling_cost_positive(self) -> None:
        s = summarize_routing(self._records())
        self.assertGreater(s["mean_coupling_cost"], 0.0)

    def test_decoupled_joint_regret_le_coupled(self) -> None:
        s = summarize_routing(self._records())
        self.assertLessEqual(s["joint_regret_decoupled"], s["joint_regret_coupled"] + 1e-9)

    def test_keys_present(self) -> None:
        s = summarize_routing(self._records())
        for k in ("mean_cer_coupled", "mean_emo_coupled", "mean_cer_decoupled", "mean_emo_decoupled",
                  "mean_coupling_cost", "joint_regret_coupled", "joint_regret_decoupled",
                  "joint_regret_always_mixed", "joint_regret_always_sep", "joint_regret_oracle"):
            self.assertIn(k, s)


if __name__ == "__main__":
    unittest.main()
