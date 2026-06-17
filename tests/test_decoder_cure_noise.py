"""Tests for the decoder-vs-input cure under-noise study (experimental/frontier).

These lock the PURE, Whisper-free aggregation logic that decides the study's verdict:

  * fire_rate / firerate_by_condition -- the H1 mechanism diagnostic: a silence-detection
    cure (energy_trim, Whisper-native halluc_silence) stops *firing* under noise (its output
    stops differing from greedy), exactly like the energy trim of #806; a path-diversity cure
    (beam5) keeps firing. The fire-rate is computed from a per-row `changed_{arm}` flag.
  * aggregate_by_condition -- per (noise_type, snr) mean CER + catastrophic tail rate per arm,
    plus the beam/halluc gains vs greedy.
  * tail_conditional -- split tracks into catastrophic (greedy CER>1) vs normal and report each
    arm's mean on each subset + the normal-majority delta (does the cure tax healthy clips?).
  * audio_agnostic_regret -- "always beam" vs always-greedy/always-flatness vs the per-track
    oracle(min). Beam is the only audio-agnostic cure, so its pooled regret-vs-oracle is the
    deployable headline.

The research motivation (does the decoder cure survive babble where input gates die?) is verified
live in the driver against Whisper; here we pin the math so the FINDINGS numbers are reproducible.
"""
from __future__ import annotations

import unittest

from src.decoder_cure_noise import (
    ARMS,
    CATASTROPHIC_CER,
    DECODER_CURES,
    INPUT_CURES,
    aggregate_by_condition,
    audio_agnostic_regret,
    fire_rate,
    firerate_by_condition,
    tail_conditional,
)


def _row(noise, snr, track, cers, changed):
    """Build a curve row. `cers` maps arm->CER; `changed` maps cure->0/1 (vs greedy)."""
    r = {"pair_id": 0, "overlap_ratio": 0.1, "noise_type": noise, "snr_db": snr, "track": track}
    for arm in ARMS:
        r[f"cer_{arm}"] = cers[arm]
    for cure in INPUT_CURES + DECODER_CURES:
        r[f"changed_{cure}"] = changed[cure]
    return r


# A 4-row fixture encoding the expected mechanism: under babble the silence detectors
# (energy_trim, halluc_silence) DO NOT fire (changed=0, CER==greedy); beam5 fires and helps.
def _fixture():
    babble_catastrophic = {
        "greedy": 3.0, "energy_trim": 3.0, "flatness_gate": 2.5, "beam5": 2.0, "halluc_silence": 3.0,
    }
    babble_changed = {"energy_trim": 0, "flatness_gate": 1, "beam5": 1, "halluc_silence": 0}
    babble_normal = {
        "greedy": 0.4, "energy_trim": 0.4, "flatness_gate": 0.5, "beam5": 0.42, "halluc_silence": 0.4,
    }
    white_catastrophic = {
        "greedy": 2.0, "energy_trim": 0.5, "flatness_gate": 0.5, "beam5": 0.6, "halluc_silence": 0.5,
    }
    white_changed = {"energy_trim": 1, "flatness_gate": 1, "beam5": 1, "halluc_silence": 1}
    return [
        _row("babble", 5.0, "spk2", babble_catastrophic, babble_changed),
        _row("babble", 5.0, "spk1", babble_normal, babble_changed),
        _row("white", 5.0, "spk2", white_catastrophic, white_changed),
        _row("white", 5.0, "spk1", babble_normal, white_changed),
    ]


class TestConstants(unittest.TestCase):
    def test_arms_partition(self):
        # greedy baseline plus the two cure families, no overlap, no omissions.
        self.assertEqual(set(ARMS), {"greedy", *INPUT_CURES, *DECODER_CURES})
        self.assertEqual(set(INPUT_CURES) & set(DECODER_CURES), set())
        self.assertIn("beam5", DECODER_CURES)
        self.assertIn("halluc_silence", DECODER_CURES)
        self.assertEqual(CATASTROPHIC_CER, 1.0)


class TestFireRate(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(fire_rate([], "beam5"), 0.0)

    def test_silence_detector_dies_path_diversity_survives(self):
        rows = _fixture()
        babble = [r for r in rows if r["noise_type"] == "babble"]
        # H1: under babble the silence detectors never fire; beam5 always does.
        self.assertEqual(fire_rate(babble, "energy_trim"), 0.0)
        self.assertEqual(fire_rate(babble, "halluc_silence"), 0.0)
        self.assertEqual(fire_rate(babble, "beam5"), 1.0)
        # under white every cure fires.
        white = [r for r in rows if r["noise_type"] == "white"]
        self.assertEqual(fire_rate(white, "halluc_silence"), 1.0)

    def test_firerate_by_condition_keys_and_values(self):
        out = firerate_by_condition(_fixture())
        babble = next(r for r in out if r["noise_type"] == "babble" and r["snr_db"] == 5.0)
        self.assertEqual(babble["n"], 2)
        self.assertEqual(babble["fire_rate_halluc_silence"], 0.0)
        self.assertEqual(babble["fire_rate_beam5"], 1.0)


class TestAggregateByCondition(unittest.TestCase):
    def test_mean_tail_and_gains(self):
        out = aggregate_by_condition(_fixture())
        babble = next(r for r in out if r["noise_type"] == "babble" and r["snr_db"] == 5.0)
        self.assertEqual(babble["n"], 2)
        # mean CER greedy = (3.0 + 0.4)/2 = 1.7 ; beam5 = (2.0 + 0.42)/2 = 1.21
        self.assertAlmostEqual(babble["mean_cer_greedy"], 1.7, places=6)
        self.assertAlmostEqual(babble["mean_cer_beam5"], 1.21, places=6)
        # tail rate (CER>1): greedy 1/2 = 0.5 ; beam5 1/2 = 0.5 (the 2.0 track)
        self.assertAlmostEqual(babble["tail_greedy"], 0.5, places=6)
        # beam gain vs greedy = mean_greedy - mean_beam = 1.7 - 1.21 = 0.49 (positive = helps)
        self.assertAlmostEqual(babble["beam_gain_vs_greedy"], 0.49, places=6)
        # halluc gain vs greedy = 0 under babble (it is inert: CER==greedy on both rows)
        self.assertAlmostEqual(babble["halluc_gain_vs_greedy"], 0.0, places=6)


class TestTailConditional(unittest.TestCase):
    def test_split_and_normal_delta(self):
        out = tail_conditional(_fixture())
        # catastrophic groups = greedy CER>1: the two spk2 rows (3.0 and 2.0). normal = two spk1 rows (0.4).
        self.assertEqual(out["n_catastrophic"], 2)
        self.assertEqual(out["n_normal"], 2)
        beam = next(a for a in out["arms"] if a["arm"] == "beam5")
        # beam mean on catastrophic = (2.0 + 0.6)/2 = 1.3
        self.assertAlmostEqual(beam["mean_cer_catastrophic"], 1.3, places=6)
        # normal-majority delta vs greedy: beam normal mean (0.42,0.42)=0.42 minus greedy normal (0.4,0.4)=0.4 => +0.02 (small tax)
        self.assertAlmostEqual(beam["normal_delta_vs_greedy"], 0.02, places=6)
        halluc = next(a for a in out["arms"] if a["arm"] == "halluc_silence")
        # halluc is inert on the babble catastrophic (3.0) but cures the white one (0.5): mean = 1.75
        self.assertAlmostEqual(halluc["mean_cer_catastrophic"], 1.75, places=6)


class TestAudioAgnosticRegret(unittest.TestCase):
    def test_oracle_and_regret_nonnegative(self):
        out = audio_agnostic_regret(_fixture())
        # oracle picks per-row min over {greedy, beam5, flatness_gate}.
        # rows: babble spk2 min(3.0,2.0,2.5)=2.0 ; babble spk1 min(0.4,0.42,0.5)=0.4 ;
        #       white spk2 min(2.0,0.6,0.5)=0.5 ; white spk1 min(0.4,0.42,0.5)=0.4 -> mean 0.825
        self.assertAlmostEqual(out["mean_cer"]["oracle"], 0.825, places=6)
        # every policy's regret vs oracle is >= 0
        for k, v in out["regret_vs_oracle"].items():
            self.assertGreaterEqual(v, -1e-9, f"{k} regret should be >= 0")
        # always_beam mean = (2.0+0.42+0.6+0.42)/4 = 0.86
        self.assertAlmostEqual(out["mean_cer"]["always_beam"], 0.86, places=6)


if __name__ == "__main__":
    unittest.main()
