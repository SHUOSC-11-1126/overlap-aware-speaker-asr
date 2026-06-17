"""Tests for the reference-free multi-gate selector (experimental/frontier).

Finding #12 (speaker_conditioned_gate) asserted that "the residual region's own spectral
flatness" is the right reference-free key to choose between the flatness gate (broadband noise)
and the speaker gate (speech-like babble) -- but never tested it, and the grid data shows a sharp
risk: at 0 dB babble the residual is speech-like (low flatness -> the naive rule says "speaker
gate") yet the speaker gate is the WORST arm there. So the selector must also carry a catastrophe
guard. These tests lock the PURE decision logic and signal extraction with an injected fake
embedder, so they run without resemblyzer / whisper installed.
"""
from __future__ import annotations

import unittest

import numpy as np

from src.gate_selector import (
    aggregate_selector,
    best_typed_policy,
    oracle_best_arm,
    pairwise_flatness_auc,
    residual_window_signal,
    select_gate,
    select_gate_utterance,
    selection_is_oracle_optimal,
)


def _tone(n: int, freq: float = 220.0, amp: float = 0.3, seed: int = 0) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / 16000.0
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _white(n: int, amp: float, seed: int) -> np.ndarray:
    return (amp * np.random.default_rng(seed).standard_normal(n)).astype(np.float32)


# Fake embedder keyed on window energy: loud target -> [1,0], quiet residual -> [0,1].
def _fake_embed(w: np.ndarray) -> np.ndarray:
    return np.array([1.0, 0.0]) if float(np.mean(np.asarray(w) ** 2)) > 0.01 else np.array([0.0, 1.0])


class TestSelectGateDecisionBoundaries(unittest.TestCase):
    """select_gate is the a-priori (no-CER) decision rule. These pin its branches."""

    def test_no_residual_means_no_gate(self) -> None:
        sig = {"has_residual": False, "residual_flatness": 0.9, "sim_gap": 0.5}
        self.assertEqual(select_gate(sig), "none")

    def test_broadband_residual_picks_flatness(self) -> None:
        sig = {"has_residual": True, "residual_flatness": 0.85, "sim_gap": 0.5}
        self.assertEqual(select_gate(sig, flat_hi=0.40), "flatness")

    def test_speechlike_residual_picks_speaker(self) -> None:
        sig = {"has_residual": True, "residual_flatness": 0.18, "sim_gap": 0.5}
        self.assertEqual(select_gate(sig, flat_hi=0.40), "speaker")

    def test_catastrophe_guard_falls_back_to_flatness(self) -> None:
        # speech-like residual BUT no clear target/residual contrast (the 0 dB babble regime):
        # the speaker gate is unsafe here, so the guard must fall back to the flatness gate.
        sig = {"has_residual": True, "residual_flatness": 0.18, "sim_gap": 0.01}
        self.assertEqual(select_gate(sig, flat_hi=0.40, min_sim_gap=0.06), "flatness")

    def test_thresholds_are_respected(self) -> None:
        sig = {"has_residual": True, "residual_flatness": 0.30, "sim_gap": 0.5}
        self.assertEqual(select_gate(sig, flat_hi=0.25), "flatness")
        self.assertEqual(select_gate(sig, flat_hi=0.50), "speaker")


class TestSelectGateUtterance(unittest.TestCase):
    """Per-utterance decision combines the two separated tracks' signals."""

    def test_any_track_broadband_uses_max_flatness(self) -> None:
        # mean residual flatness across has-residual tracks drives the broadband decision
        t1 = {"has_residual": True, "residual_flatness": 0.9, "sim_gap": 0.5}
        t2 = {"has_residual": True, "residual_flatness": 0.8, "sim_gap": 0.5}
        self.assertEqual(select_gate_utterance([t1, t2], flat_hi=0.40), "flatness")

    def test_worst_case_sim_gap_triggers_guard(self) -> None:
        # one track is recoverable, the other is collapsed (0 dB); min sim_gap must win -> guard
        t1 = {"has_residual": True, "residual_flatness": 0.18, "sim_gap": 0.5}
        t2 = {"has_residual": True, "residual_flatness": 0.18, "sim_gap": 0.01}
        self.assertEqual(select_gate_utterance([t1, t2], flat_hi=0.40, min_sim_gap=0.06), "flatness")

    def test_speechlike_recoverable_picks_speaker(self) -> None:
        t1 = {"has_residual": True, "residual_flatness": 0.2, "sim_gap": 0.4}
        t2 = {"has_residual": True, "residual_flatness": 0.15, "sim_gap": 0.3}
        self.assertEqual(select_gate_utterance([t1, t2], flat_hi=0.40), "speaker")

    def test_no_residual_anywhere_is_none(self) -> None:
        t1 = {"has_residual": False, "residual_flatness": 0.0, "sim_gap": 0.0}
        t2 = {"has_residual": False, "residual_flatness": 0.0, "sim_gap": 0.0}
        self.assertEqual(select_gate_utterance([t1, t2]), "none")


class TestResidualWindowSignal(unittest.TestCase):
    """Signal extraction is reference-free: only the audio + an injected embedder."""

    def test_broadband_residual_has_high_flatness(self) -> None:
        # [quiet white-noise residual][loud tone target][quiet white-noise residual]; residual
        # regions are several windows long so the similarity valley is well-formed.
        win = 25600
        res1 = _white(win * 3, amp=0.02, seed=1)
        tgt = _tone(win * 2, amp=0.4)
        x = np.concatenate([res1, tgt, _white(win * 3, amp=0.02, seed=2)]).astype(np.float32)
        sig = residual_window_signal(x, _fake_embed)
        self.assertTrue(sig["has_residual"])
        self.assertGreater(sig["residual_flatness"], 0.4)  # white noise -> flat

    def test_speechlike_residual_has_low_flatness(self) -> None:
        # [quiet tone residual][loud tone target][quiet tone residual]: peaky residual -> low flatness
        win = 25600
        res = _tone(win * 3, freq=130.0, amp=0.02)
        tgt = _tone(win * 2, freq=220.0, amp=0.4)
        x = np.concatenate([res, tgt, _tone(win * 3, freq=130.0, amp=0.02)]).astype(np.float32)
        sig = residual_window_signal(x, _fake_embed)
        self.assertTrue(sig["has_residual"])
        self.assertLess(sig["residual_flatness"], 0.4)  # tone -> peaky

    def test_all_target_has_no_residual(self) -> None:
        # uniform loud tone: no quiet residual region to crop
        x = _tone(25600 * 4, amp=0.4)
        sig = residual_window_signal(x, _fake_embed)
        self.assertFalse(sig["has_residual"])

    def test_signal_keys_present(self) -> None:
        x = np.concatenate([_white(25600, 0.02, 3), _tone(51200, amp=0.4)]).astype(np.float32)
        sig = residual_window_signal(x, _fake_embed)
        for k in ("has_residual", "residual_flatness", "sim_gap", "residual_frac"):
            self.assertIn(k, sig)


class TestOracleAndSelectionAccuracy(unittest.TestCase):
    def test_oracle_best_arm(self) -> None:
        row = {"cer_sep": 0.5, "cer_flatness_gate": 0.3, "cer_speaker_gate": 0.7}
        self.assertEqual(oracle_best_arm(row), "flatness")
        row2 = {"cer_sep": 0.5, "cer_flatness_gate": 0.9, "cer_speaker_gate": 0.2}
        self.assertEqual(oracle_best_arm(row2), "speaker")
        row3 = {"cer_sep": 0.1, "cer_flatness_gate": 0.9, "cer_speaker_gate": 0.8}
        self.assertEqual(oracle_best_arm(row3), "none")

    def test_selection_optimality(self) -> None:
        row = {"cer_sep": 0.5, "cer_flatness_gate": 0.3, "cer_speaker_gate": 0.7, "selected_gate": "flatness"}
        self.assertTrue(selection_is_oracle_optimal(row))
        row_bad = {"cer_sep": 0.5, "cer_flatness_gate": 0.3, "cer_speaker_gate": 0.7, "selected_gate": "speaker"}
        self.assertFalse(selection_is_oracle_optimal(row_bad))


class TestAggregateSelector(unittest.TestCase):
    """aggregate_selector pools the grid by (noise_type, snr) with selector + oracle CER, the
    selector's realized CER (the picked arm), tail rates, regret vs oracle, and selection
    accuracy. CER is post-hoc only -- never an input to the pick."""

    def _rows(self) -> list[dict]:
        # 2 conditions x 2 samples. Selector picks via 'selected_gate'; cer_selector is the
        # realized CER of the picked arm; oracle is the per-row min.
        return [
            {"noise_type": "white", "snr_db": 10.0, "cer_mixed": 0.6, "cer_sep": 0.5,
             "cer_flatness_gate": 0.2, "cer_speaker_gate": 0.6, "selected_gate": "flatness",
             "cer_selector": 0.2},
            {"noise_type": "white", "snr_db": 10.0, "cer_mixed": 0.6, "cer_sep": 0.4,
             "cer_flatness_gate": 0.3, "cer_speaker_gate": 0.5, "selected_gate": "flatness",
             "cer_selector": 0.3},
            {"noise_type": "babble", "snr_db": 10.0, "cer_mixed": 0.7, "cer_sep": 1.6,
             "cer_flatness_gate": 0.8, "cer_speaker_gate": 0.6, "selected_gate": "speaker",
             "cer_selector": 0.6},
            {"noise_type": "babble", "snr_db": 0.0, "cer_mixed": 0.7, "cer_sep": 2.9,
             "cer_flatness_gate": 1.4, "cer_speaker_gate": 3.1, "selected_gate": "flatness",
             "cer_selector": 1.4},
        ]

    def test_pooled_means_and_regret(self) -> None:
        agg = aggregate_selector(self._rows())
        pooled = agg["pooled"]
        self.assertEqual(pooled["n"], 4)
        # selector mean = mean(0.2,0.3,0.6,1.4) = 0.625
        self.assertAlmostEqual(pooled["mean_cer_selector"], 0.625, places=4)
        # oracle mean = mean(0.2,0.3,0.6,1.4) = 0.625 here (selector matched oracle on all rows)
        self.assertAlmostEqual(pooled["mean_cer_oracle"], 0.625, places=4)
        self.assertAlmostEqual(pooled["regret_vs_oracle"], 0.0, places=4)

    def test_selection_accuracy(self) -> None:
        agg = aggregate_selector(self._rows())
        # all 4 rows pick the oracle-best arm -> accuracy 1.0
        self.assertAlmostEqual(agg["pooled"]["selection_accuracy"], 1.0, places=4)

    def test_per_condition_breakdown(self) -> None:
        agg = aggregate_selector(self._rows())
        keys = {(r["noise_type"], r["snr_db"]) for r in agg["by_condition"]}
        self.assertIn(("white", 10.0), keys)
        self.assertIn(("babble", 0.0), keys)

    def test_selector_beats_each_fixed_arm_here(self) -> None:
        agg = aggregate_selector(self._rows())
        p = agg["pooled"]
        # constructed so selector (0.625) < always-flatness (0.675) and < always-speaker (1.2)
        self.assertLess(p["mean_cer_selector"], p["mean_cer_flatness_gate"])
        self.assertLess(p["mean_cer_selector"], p["mean_cer_speaker_gate"])
        self.assertLess(p["mean_cer_selector"], p["mean_cer_sep"])


class TestPairwiseFlatnessAndCeiling(unittest.TestCase):
    def _rows(self) -> list[dict]:
        # white residual flatness clearly > pink > babble; arm CERs let the ceiling pick per type.
        return [
            {"noise_type": "white", "snr_db": 10.0, "residual_flatness_max": 0.55,
             "cer_mixed": 0.6, "cer_sep": 0.5, "cer_flatness_gate": 0.3, "cer_speaker_gate": 0.8},
            {"noise_type": "pink", "snr_db": 10.0, "residual_flatness_max": 0.17,
             "cer_mixed": 0.6, "cer_sep": 0.4, "cer_flatness_gate": 0.9, "cer_speaker_gate": 0.5},
            {"noise_type": "babble", "snr_db": 10.0, "residual_flatness_max": 0.09,
             "cer_mixed": 0.6, "cer_sep": 1.6, "cer_flatness_gate": 1.2, "cer_speaker_gate": 0.4},
        ]

    def test_pairwise_auc_separates_types(self) -> None:
        pw = pairwise_flatness_auc(self._rows())
        # single-sample-per-type but strictly ordered -> all AUC 1.0
        self.assertEqual(pw["auc_white_vs_babble"], 1.0)
        self.assertEqual(pw["auc_pink_vs_babble"], 1.0)
        self.assertEqual(pw["auc_white_vs_pink"], 1.0)
        self.assertGreater(pw["mean_residual_flatness"]["white"], pw["mean_residual_flatness"]["pink"])

    def test_best_typed_policy_picks_min_arm_per_type(self) -> None:
        ceil = best_typed_policy(self._rows())
        # white: min is flatness(0.3); pink: min is none/sep(0.4); babble: min is speaker(0.4)
        self.assertEqual(ceil["per_type_arm"], {"white": "flatness", "pink": "none", "babble": "speaker"})
        # pooled ceiling CER = mean(0.3, 0.4, 0.4) = 0.366667
        self.assertAlmostEqual(ceil["mean_cer"], 0.366667, places=4)


if __name__ == "__main__":
    unittest.main()
