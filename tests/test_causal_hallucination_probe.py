"""Tests for the causal & internal-state hallucination probe (experimental/frontier).

Pin the PURE helpers: compression ratio (Whisper-faithful), causal-prefix CR latency,
token-repetition lock-in latency, token-id entropy / dominant-token fraction, the
confident-loop anomaly composite, rank-AUC, and the causal-deployability regret
simulation. No Whisper / no audio needed (signals are passed in as plain values).
"""
from __future__ import annotations

import unittest

import numpy as np

from src.causal_hallucination_probe import (
    confident_loop_anomaly,
    cr_causal_latency_fraction,
    deployability_regrets,
    dominant_token_fraction,
    lockin_latency_fraction,
    prefix_compression_ratios,
    repetition_lockin_index,
    summarize_probe,
    token_id_entropy,
)


class TestCompressionRatio(unittest.TestCase):
    def test_repetitive_text_has_high_ratio(self) -> None:
        from src.causal_hallucination_probe import compression_ratio

        repetitive = "小小小小小小小小小小小小"
        normal = "今天天气真好我们去公园散步吧"
        self.assertGreater(compression_ratio(repetitive), compression_ratio(normal))

    def test_empty_is_zero(self) -> None:
        from src.causal_hallucination_probe import compression_ratio

        self.assertEqual(compression_ratio(""), 0.0)

    def test_prefix_curve_monotone_for_runaway_repeat(self) -> None:
        # a runaway repetition: CR over growing prefixes should climb and stay high
        text = "啊" * 200
        curve = prefix_compression_ratios(text, fracs=[0.1, 0.3, 0.5, 1.0])
        self.assertEqual(len(curve), 4)
        # once the repeat is established, every prefix is highly compressible
        self.assertGreater(curve[-1], 2.4)


class TestCausalLatency(unittest.TestCase):
    def test_cr_latency_fires_for_repetitive(self) -> None:
        text = "小" * 200
        lat = cr_causal_latency_fraction(text, threshold=2.4, n_steps=40)
        self.assertIsNotNone(lat)
        self.assertGreaterEqual(lat, 0.0)
        self.assertLessEqual(lat, 1.0)

    def test_cr_latency_none_for_normal_text(self) -> None:
        # diverse text should never cross the degeneracy threshold
        text = "今天天气真好我们去公园散步吧顺便买点水果回家"
        lat = cr_causal_latency_fraction(text, threshold=2.4, n_steps=40)
        self.assertIsNone(lat)

    def test_lockin_index_basic_run(self) -> None:
        # token 7322 repeats starting at index 0; first lock-in (run>=3) detected at index 2
        toks = [7322, 7322, 7322, 7322, 7322]
        self.assertEqual(repetition_lockin_index(toks, min_run=3), 2)

    def test_lockin_index_later_run(self) -> None:
        toks = [1, 2, 3, 4, 4, 4, 4]
        # run of 4s reaches length 3 at window ending index 5 (tokens[3],tokens[4],tokens[5])
        self.assertEqual(repetition_lockin_index(toks, min_run=3), 5)

    def test_lockin_index_none_when_diverse(self) -> None:
        self.assertIsNone(repetition_lockin_index([1, 2, 3, 4, 5], min_run=3))

    def test_lockin_catches_phrase_loop(self) -> None:
        # a 6-token phrase repeated -> period-6 lock-in (the con_006/pro_006 case)
        phrase = [10, 11, 12, 13, 14, 15]
        toks = phrase * 5  # 30 tokens, "你是不是在那里" x5 analogue
        idx = repetition_lockin_index(toks, min_run=3, max_period=12)
        self.assertIsNotNone(idx)
        # 3 reps of a length-6 unit complete at index 17 (tokens[0..17])
        self.assertEqual(idx, 17)

    def test_lockin_p1_subsumed_by_period_detection(self) -> None:
        # single-token loop must still be caught at the same index as before
        self.assertEqual(repetition_lockin_index([7322, 7322, 7322, 7322, 7322], min_run=3), 2)

    def test_lockin_latency_fraction_early_for_long_loop(self) -> None:
        # 224-token loop locks in at index 2 -> fraction ~2/223 (very early)
        toks = [7322] + [7322] * 223
        frac = lockin_latency_fraction(toks, min_run=3)
        self.assertIsNotNone(frac)
        self.assertLess(frac, 0.05)

    def test_lockin_latency_none_for_diverse(self) -> None:
        self.assertIsNone(lockin_latency_fraction([1, 2, 3, 4, 5], min_run=3))


class TestEntropyAndDominant(unittest.TestCase):
    def test_all_same_token_zero_entropy(self) -> None:
        self.assertAlmostEqual(token_id_entropy([7, 7, 7, 7]), 0.0, places=9)

    def test_diverse_tokens_high_entropy(self) -> None:
        self.assertGreater(token_id_entropy([1, 2, 3, 4, 5, 6, 7, 8]), 1.5)

    def test_dominant_fraction_all_same(self) -> None:
        self.assertAlmostEqual(dominant_token_fraction([5, 5, 5, 5]), 1.0, places=9)

    def test_dominant_fraction_balanced(self) -> None:
        self.assertAlmostEqual(dominant_token_fraction([1, 2, 3, 4]), 0.25, places=9)


class TestConfidentLoopAnomaly(unittest.TestCase):
    def test_catastrophic_signature(self) -> None:
        # encoder says "no speech" (high nsp), decoder confident (avg_logprob near 0), locked repeat
        a = confident_loop_anomaly(no_speech_prob=0.82, avg_logprob=-0.065, tokens=[7322] * 50)
        self.assertGreater(a["no_speech_prob"], 0.6)
        self.assertGreater(a["decoder_confidence"], 0.9)  # exp(-0.065) ~ 0.937
        self.assertGreater(a["dominant_token_fraction"], 0.95)
        self.assertGreater(a["confident_silent_score"], 0.5)  # nsp * confidence

    def test_clean_track_signature(self) -> None:
        a = confident_loop_anomaly(no_speech_prob=0.05, avg_logprob=-0.6, tokens=list(range(40)))
        self.assertLess(a["confident_silent_score"], 0.1)
        self.assertLess(a["dominant_token_fraction"], 0.1)


class TestDeployabilityRegrets(unittest.TestCase):
    def _rows(self) -> list[dict]:
        # 6 conditions: 2 catastrophic sep (would need abort), 4 clean sep.
        # catastrophic: sep CER huge, mixed small; clean: sep small, mixed larger.
        return [
            # cond, cer_mixed, cer_sep, catastrophic, cr_lat_frac, lockin_lat_frac
            {"id": "c0", "cer_mixed": 0.3, "cer_sep": 12.0, "catastrophic": True,
             "cr_lat_frac": 0.6, "lockin_lat_frac": 0.02},
            {"id": "c1", "cer_mixed": 0.4, "cer_sep": 8.0, "catastrophic": True,
             "cr_lat_frac": 0.7, "lockin_lat_frac": 0.03},
            {"id": "c2", "cer_mixed": 0.5, "cer_sep": 0.2, "catastrophic": False,
             "cr_lat_frac": None, "lockin_lat_frac": None},
            {"id": "c3", "cer_mixed": 0.6, "cer_sep": 0.25, "catastrophic": False,
             "cr_lat_frac": None, "lockin_lat_frac": None},
            {"id": "c4", "cer_mixed": 0.45, "cer_sep": 0.3, "catastrophic": False,
             "cr_lat_frac": None, "lockin_lat_frac": None},
            {"id": "c5", "cer_mixed": 0.55, "cer_sep": 0.22, "catastrophic": False,
             "cr_lat_frac": None, "lockin_lat_frac": None},
        ]

    def test_offline_guard_beats_fixed_sep(self) -> None:
        out = deployability_regrets(self._rows(), abort_frac_cap=0.5)
        # offline guard sees full segment -> catches both catastrophes -> lowest regret
        self.assertLess(out["offline_guard_regret"], out["fixed_sep_regret"])
        self.assertLess(out["offline_guard_regret"], out["fixed_mixed_regret"])

    def test_causal_internal_beats_causal_cr(self) -> None:
        # lock-in fires within cap (0.02,0.03 < 0.5) on both catastrophes -> catches them
        # CR fires at 0.6,0.7 > 0.5 cap -> misses them -> commits to catastrophic sep
        out = deployability_regrets(self._rows(), abort_frac_cap=0.5)
        self.assertLess(out["causal_internal_regret"], out["causal_cr_regret"])

    def test_causal_cr_loses_vs_offline_when_latency_exceeds_cap(self) -> None:
        # because CR latency (0.6/0.7) > cap (0.5), causal-CR misses both -> ~fixed_sep
        out = deployability_regrets(self._rows(), abort_frac_cap=0.5)
        self.assertGreaterEqual(out["causal_cr_regret"], out["offline_guard_regret"])

    def test_oracle_is_floor(self) -> None:
        out = deployability_regrets(self._rows(), abort_frac_cap=0.5)
        self.assertLessEqual(out["oracle_cer"], out["offline_guard_cer"])


class TestSummarize(unittest.TestCase):
    def test_summarize_partitions_catastrophic(self) -> None:
        rows = [
            {"catastrophic": True, "no_speech_prob": 0.8, "avg_logprob": -0.07,
             "token_entropy": 0.1, "dominant_token_fraction": 0.98,
             "cr_lat_frac": 0.5, "lockin_lat_frac": 0.02, "cer_sep": 12.0},
            {"catastrophic": False, "no_speech_prob": 0.1, "avg_logprob": -0.5,
             "token_entropy": 3.2, "dominant_token_fraction": 0.1,
             "cr_lat_frac": None, "lockin_lat_frac": None, "cer_sep": 0.2},
        ]
        s = summarize_probe(rows)
        self.assertIn("mechanism", s)
        mech = s["mechanism"]
        # catastrophic has higher no_speech_prob, higher avg_logprob (less negative), lower entropy
        self.assertGreater(mech["catastrophic_mean_no_speech_prob"], mech["clean_mean_no_speech_prob"])
        self.assertGreater(mech["catastrophic_mean_avg_logprob"], mech["clean_mean_avg_logprob"])
        self.assertLess(mech["catastrophic_mean_token_entropy"], mech["clean_mean_token_entropy"])
        # latency: lock-in fires earlier than CR where both exist
        self.assertIn("latency", s)


if __name__ == "__main__":
    unittest.main()
