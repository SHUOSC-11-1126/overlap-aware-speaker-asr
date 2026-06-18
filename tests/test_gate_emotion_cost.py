"""Tests for the gate emotion-cost analysis (experimental/frontier).

Pin the pure aggregation: per-gate mean CER benefit (does the gate cure CER?) vs mean emotion cost
(does the gate add prosody distortion vs raw separation?), and the trade-off correlation. No Whisper/
librosa (CER and prosody distortions are passed in).
"""
from __future__ import annotations

import unittest

from src.gate_emotion_cost import aggregate_gate_cost


class TestAggregateGateCost(unittest.TestCase):
    def _rows(self):
        # a gate that cures CER (positive benefit) but adds prosody distortion (positive cost)
        return [
            {"gate": "speaker", "cer_raw": 1.6, "cer_gated": 0.7, "dist_raw": 0.10, "dist_gated": 0.25},
            {"gate": "speaker", "cer_raw": 1.5, "cer_gated": 0.8, "dist_raw": 0.12, "dist_gated": 0.22},
            {"gate": "flatness", "cer_raw": 1.6, "cer_gated": 1.5, "dist_raw": 0.10, "dist_gated": 0.11},
            {"gate": "flatness", "cer_raw": 1.5, "cer_gated": 1.4, "dist_raw": 0.12, "dist_gated": 0.13},
        ]

    def test_per_gate_means(self) -> None:
        agg = aggregate_gate_cost(self._rows())
        spk = next(g for g in agg["by_gate"] if g["gate"] == "speaker")
        self.assertAlmostEqual(spk["mean_cer_benefit"], 0.8, places=6)     # (0.9+0.7)/2
        self.assertAlmostEqual(spk["mean_emotion_cost"], 0.125, places=6)  # (0.15+0.10)/2

    def test_speaker_gate_has_emotion_cost(self) -> None:
        agg = aggregate_gate_cost(self._rows())
        spk = next(g for g in agg["by_gate"] if g["gate"] == "speaker")
        self.assertGreater(spk["mean_emotion_cost"], 0.0)   # cures CER but damages emotion
        self.assertGreater(spk["mean_cer_benefit"], 0.0)

    def test_keys_present(self) -> None:
        agg = aggregate_gate_cost(self._rows())
        self.assertIn("by_gate", agg)
        for g in agg["by_gate"]:
            for k in ("gate", "n", "mean_cer_benefit", "mean_emotion_cost"):
                self.assertIn(k, g)


if __name__ == "__main__":
    unittest.main()
