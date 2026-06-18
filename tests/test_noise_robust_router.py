"""Unit tests for the reference-free noise-robust router (issue #814).

Pure routing + evaluation logic tested offline on synthetic rows (no Whisper/resemblyzer). The grid
collector that needs Whisper is exercised separately by a real run. Must pass under `unittest discover`.
"""
from __future__ import annotations

import math
import unittest

from src import noise_robust_router as nrr


class TestGatedDegeneracy(unittest.TestCase):
    def test_aggregates_two_tracks(self):
        s1 = {"max_compression_ratio": 1.8, "repetition_count": 1, "mean_avg_logprob": -0.5, "max_no_speech_prob": 0.2}
        s2 = {"max_compression_ratio": 3.1, "repetition_count": 4, "mean_avg_logprob": -1.5, "max_no_speech_prob": 0.6}
        d = nrr.gated_degeneracy(s1, s2)
        self.assertAlmostEqual(d["max_compression_ratio"], 3.1)   # max across tracks
        self.assertEqual(d["repetition_count"], 5)                 # sum
        self.assertAlmostEqual(d["mean_logprob"], -1.0)            # mean
        self.assertAlmostEqual(d["max_no_speech_prob"], 0.6)       # max


class TestRoute(unittest.TestCase):
    def test_high_compression_routes_to_mixed(self):
        d = {"max_compression_ratio": 3.0, "repetition_count": 0, "mean_logprob": -0.5, "max_no_speech_prob": 0.1}
        self.assertEqual(nrr.route(d, cr_guard=2.4), "mixed")

    def test_high_repetition_routes_to_mixed(self):
        d = {"max_compression_ratio": 1.0, "repetition_count": 6, "mean_logprob": -0.5, "max_no_speech_prob": 0.1}
        self.assertEqual(nrr.route(d, cr_guard=2.4, rep_guard=4), "mixed")

    def test_clean_routes_to_separate_gate(self):
        d = {"max_compression_ratio": 1.2, "repetition_count": 0, "mean_logprob": -0.3, "max_no_speech_prob": 0.05}
        self.assertEqual(nrr.route(d, cr_guard=2.4), "separate_gate")


class TestEvaluate(unittest.TestCase):
    def _rows(self):
        # 4 conditions: at low overlap mixed wins; at high overlap gate wins; degeneracy (CR) flags
        # the cases where the gated output is hallucinated (gate worse than mixed).
        return [
            # low overlap, gate degenerate (high CR) -> should route mixed (correct: mixed better)
            {"overlap_ratio": 0.0, "cer_mixed": 0.30, "cer_speaker_gate": 1.20,
             "max_compression_ratio": 3.5, "repetition_count": 5, "mean_logprob": -2.0, "max_no_speech_prob": 0.3},
            {"overlap_ratio": 0.1, "cer_mixed": 0.40, "cer_speaker_gate": 0.90,
             "max_compression_ratio": 2.8, "repetition_count": 3, "mean_logprob": -1.5, "max_no_speech_prob": 0.2},
            # high overlap, gate clean (low CR) -> should route separate_gate (correct: gate better)
            {"overlap_ratio": 0.6, "cer_mixed": 1.20, "cer_speaker_gate": 0.50,
             "max_compression_ratio": 1.1, "repetition_count": 0, "mean_logprob": -0.4, "max_no_speech_prob": 0.05},
            {"overlap_ratio": 0.8, "cer_mixed": 1.40, "cer_speaker_gate": 0.60,
             "max_compression_ratio": 1.3, "repetition_count": 1, "mean_logprob": -0.5, "max_no_speech_prob": 0.08},
        ]

    def test_router_beats_both_fixed(self):
        out = nrr.evaluate(self._rows(), cr_guard=2.4, rep_guard=4)
        p = out["pooled"]
        # oracle picks min per row: (0.30, 0.40, 0.50, 0.60) -> 0.45
        self.assertAlmostEqual(p["mean_cer_oracle"], 0.45, places=4)
        # router routes first two to mixed (0.30,0.40), last two to gate (0.50,0.60) = oracle here
        self.assertAlmostEqual(p["mean_cer_router"], 0.45, places=4)
        self.assertLess(p["mean_cer_router"], p["mean_cer_mixed"])         # H1 vs always-mixed (0.825)
        self.assertLess(p["mean_cer_router"], p["mean_cer_speaker_gate"])  # H1 vs always-gate (0.80)
        self.assertTrue(out["H1_router_beats_both_fixed"])

    def test_regret_and_oracle_gap(self):
        out = nrr.evaluate(self._rows(), cr_guard=2.4, rep_guard=4)
        self.assertAlmostEqual(out["pooled"]["regret_vs_oracle"], 0.0, places=4)  # perfect routing here
        self.assertIn("oracle_gap_recovered", out["pooled"])

    def test_by_overlap_present(self):
        out = nrr.evaluate(self._rows(), cr_guard=2.4, rep_guard=4)
        ov = {r["overlap_ratio"] for r in out["by_overlap"]}
        self.assertEqual(ov, {0.0, 0.1, 0.6, 0.8})

    def test_h3_degeneracy_tracks_tax(self):
        # high CR should coincide with gate being worse than mixed (cer_gate - cer_mixed > 0)
        out = nrr.evaluate(self._rows(), cr_guard=2.4, rep_guard=4)
        self.assertIn("H3_degeneracy_tracks_tax", out)
        self.assertIn("pearson_cr_vs_gate_minus_mixed", out["pooled"])

    def test_empty_safe(self):
        out = nrr.evaluate([], cr_guard=2.4)
        self.assertEqual(out["pooled"]["n"], 0)
        self.assertTrue(math.isnan(out["pooled"]["mean_cer_router"]))


if __name__ == "__main__":
    unittest.main()
