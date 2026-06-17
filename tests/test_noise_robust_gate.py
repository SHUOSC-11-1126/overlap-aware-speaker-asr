"""Tests for the noise-robust spectral-flatness speech gate (experimental/frontier).

These cover the PURE, Whisper-free primitives that decide which span of a separated
track to keep before ASR. The research motivation (energy trim dies under noise,
flatness still separates speech from noise-residual) is verified live in the driver;
here we lock the building blocks: flatness discriminates tone vs noise, the adaptive
threshold finds the valley of a bimodal flatness distribution (and abstains when the
distribution is unimodal), and flatness_trim crops leading/trailing residual while
leaving clean speech untouched.
"""
from __future__ import annotations

import unittest

import numpy as np

from src.noise_robust_gate import (
    adaptive_flatness_threshold,
    aggregate_by_snr,
    flatness_relenergy_trim,
    flatness_trim,
    frame_energy,
    frame_signal,
    mask_to_span,
    relenergy_speech_mask,
    selective_gate_policy,
    spectral_flatness,
    track_flatness,
)

SR = 16000


def _tone(n: int, freq: float = 220.0, amp: float = 0.3, seed: int = 0) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / SR
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _noise(n: int, amp: float = 0.05, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return (amp * rng.standard_normal(n)).astype(np.float32)


class TestFrameSignal(unittest.TestCase):
    def test_shape(self) -> None:
        x = np.zeros(16000, dtype=np.float32)
        fr = frame_signal(x, win=400, hop=160)
        self.assertEqual(fr.shape[1], 400)
        # n_frames = 1 + (16000-400)//160
        self.assertEqual(fr.shape[0], 1 + (16000 - 400) // 160)

    def test_too_short_returns_empty(self) -> None:
        fr = frame_signal(np.zeros(100, dtype=np.float32), win=400, hop=160)
        self.assertEqual(fr.shape, (0, 400))


class TestSpectralFlatness(unittest.TestCase):
    def test_tone_low_noise_high(self) -> None:
        tone = frame_signal(_tone(16000), 400, 160)
        noise = frame_signal(_noise(16000, amp=0.3, seed=1), 400, 160)
        ft = float(np.mean(spectral_flatness(tone)))
        fn = float(np.mean(spectral_flatness(noise)))
        self.assertLess(ft, 0.1)          # harmonic -> peaky spectrum -> low flatness
        self.assertGreater(fn, 0.3)       # broadband noise -> flatter spectrum
        self.assertLess(ft, fn)

    def test_range_bounds(self) -> None:
        fl = spectral_flatness(frame_signal(_noise(16000, 0.2, 2), 400, 160))
        self.assertTrue(np.all(fl >= 0.0))
        self.assertTrue(np.all(fl <= 1.0 + 1e-6))

    def test_zero_frame_is_flat(self) -> None:
        # A true-silent (all-zero) frame has no spectral structure -> flatness ~ 1.0,
        # so it reads as "non-speech" exactly like noise (we want to crop it).
        z = np.zeros((1, 400), dtype=np.float32)
        self.assertGreater(float(spectral_flatness(z)[0]), 0.9)

    def test_empty_frames(self) -> None:
        self.assertEqual(spectral_flatness(np.zeros((0, 400), dtype=np.float32)).shape, (0,))


class TestAdaptiveThreshold(unittest.TestCase):
    def test_bimodal_returns_valley(self) -> None:
        flat = np.concatenate([np.full(50, 0.05), np.full(50, 0.95)]).astype(np.float32)
        thr = adaptive_flatness_threshold(flat)
        self.assertIsNotNone(thr)
        assert thr is not None
        self.assertGreater(thr, 0.05)
        self.assertLess(thr, 0.95)

    def test_unimodal_abstains(self) -> None:
        # All-speech (uniformly low) or all-noise (uniformly high) -> no clear split.
        self.assertIsNone(adaptive_flatness_threshold(np.full(100, 0.06, dtype=np.float32)))
        self.assertIsNone(adaptive_flatness_threshold(np.full(100, 0.93, dtype=np.float32)))

    def test_empty_abstains(self) -> None:
        self.assertIsNone(adaptive_flatness_threshold(np.zeros((0,), dtype=np.float32)))


class TestMaskToSpan(unittest.TestCase):
    def test_contiguous_span(self) -> None:
        mask = np.array([False, False, True, True, False, True, False])
        self.assertEqual(mask_to_span(mask), (2, 6))  # first True .. last True + 1

    def test_no_true(self) -> None:
        self.assertEqual(mask_to_span(np.zeros(5, dtype=bool)), (0, 0))


class TestRelEnergyMask(unittest.TestCase):
    def test_relative_to_floor(self) -> None:
        # frames: mostly quiet (noise floor) + a few loud (speech) -> loud flagged speech
        frames = np.concatenate([
            _noise(400 * 80, 0.02, 3).reshape(80, 400),
            _tone(400 * 20).reshape(20, 400),
        ])
        mask = relenergy_speech_mask(frames, floor_pct=20, factor=3.0)
        self.assertTrue(mask[-5:].all())          # loud tone frames -> speech
        self.assertFalse(mask[:5].any())          # quiet noise-floor frames -> not speech

    def test_frame_energy_matches_mean_square(self) -> None:
        fr = _tone(400 * 3).reshape(3, 400)
        e = frame_energy(fr)
        self.assertEqual(e.shape, (3,))
        self.assertTrue(np.allclose(e, np.mean(fr ** 2, axis=1)))


class TestFlatnessTrim(unittest.TestCase):
    def _track(self, snr_amp: float, seed: int) -> tuple[np.ndarray, int, int]:
        """[noise | tone | noise] -- speech in the middle third."""
        n = 16000
        speech = _tone(n)
        track = _noise(3 * n, amp=snr_amp, seed=seed)
        track[n:2 * n] += speech  # speech rides on noise in the middle
        return track, n, 2 * n

    def test_crops_to_speech_region_clean(self) -> None:
        track, s, e = self._track(snr_amp=0.0, seed=4)  # silent ends (true zeros)
        out = flatness_trim(track, margin_samples=1600)
        self.assertLess(len(out), len(track))                 # cropped
        self.assertGreater(len(out), (e - s) - 4000)          # kept ~the speech region

    def test_crops_under_noise(self) -> None:
        # The whole point: with additive noise the residual ends are NOT silent, yet
        # the flatness gate still crops them (energy trim would keep everything).
        track, s, e = self._track(snr_amp=0.05, seed=5)
        out = flatness_trim(track, margin_samples=1600)
        self.assertLess(len(out), int(0.85 * len(track)))

    def test_all_speech_unchanged(self) -> None:
        track = _tone(2 * 16000) + _noise(2 * 16000, 0.02, 6)
        out = flatness_trim(track, margin_samples=1600)
        self.assertEqual(len(out), len(track))                # unimodal -> abstain -> keep all

    def test_deterministic(self) -> None:
        track, _, _ = self._track(snr_amp=0.05, seed=7)
        self.assertTrue(np.array_equal(flatness_trim(track), flatness_trim(track)))

    def test_short_input_unchanged(self) -> None:
        short = _tone(200)
        self.assertTrue(np.array_equal(flatness_trim(short), short))


class TestFlatnessRelEnergyTrim(unittest.TestCase):
    def test_crops_under_noise(self) -> None:
        n = 16000
        track = _noise(3 * n, amp=0.05, seed=8)
        track[n:2 * n] += _tone(n)
        out = flatness_relenergy_trim(track, margin_samples=1600)
        self.assertLess(len(out), len(track))

    def test_all_speech_unchanged(self) -> None:
        track = _tone(2 * 16000) + _noise(2 * 16000, 0.02, 9)
        out = flatness_relenergy_trim(track, margin_samples=1600)
        self.assertEqual(len(out), len(track))


class TestAggregateBySnr(unittest.TestCase):
    def test_per_snr_means_deltas_and_fire_rate(self) -> None:
        rows = [
            # clean: flatness gate beats raw sep and energy trim; both gates fired
            {"snr_db": "None", "cer_mixed": "0.5", "cer_sep": "0.9", "cer_energy_trim": "0.4",
             "cer_flatness_gate": "0.3", "cer_flatness_relenergy_gate": "0.3",
             "fired_energy_trim": "1", "fired_flatness_gate": "1", "fired_flatness_relenergy_gate": "1"},
            # 0 dB: energy trim DEAD (== sep, did not fire); flatness gate still fired + helped
            {"snr_db": "0.0", "cer_mixed": "1.0", "cer_sep": "1.4", "cer_energy_trim": "1.4",
             "cer_flatness_gate": "1.1", "cer_flatness_relenergy_gate": "1.2",
             "fired_energy_trim": "0", "fired_flatness_gate": "1", "fired_flatness_relenergy_gate": "1"},
        ]
        by = {str(g["snr_db"]): g for g in aggregate_by_snr(rows)}
        clean, zero = by["clean"], by["0.0"]
        self.assertEqual(clean["n"], 1)
        self.assertAlmostEqual(clean["mean_cer_flatness_gate"], 0.3)
        self.assertAlmostEqual(clean["flatness_gain_vs_sep"], 0.6)          # 0.9 - 0.3
        self.assertAlmostEqual(clean["flatness_gain_vs_energytrim"], 0.1)   # 0.4 - 0.3
        # at 0 dB the energy trim is dead (fire rate 0, no gain) but the flatness gate fired
        self.assertAlmostEqual(zero["fire_rate_energy_trim"], 0.0)
        self.assertAlmostEqual(zero["energytrim_gain_vs_sep"], 0.0)
        self.assertAlmostEqual(zero["fire_rate_flatness_gate"], 1.0)
        self.assertGreater(zero["flatness_gain_vs_sep"], 0.0)

    def test_tail_rate(self) -> None:
        rows = [
            {"snr_db": "5.0", "cer_mixed": "0.5", "cer_sep": "2.0", "cer_energy_trim": "2.0",
             "cer_flatness_gate": "0.5", "cer_flatness_relenergy_gate": "0.6",
             "fired_energy_trim": "0", "fired_flatness_gate": "1", "fired_flatness_relenergy_gate": "1"},
            {"snr_db": "5.0", "cer_mixed": "0.5", "cer_sep": "0.5", "cer_energy_trim": "0.5",
             "cer_flatness_gate": "0.5", "cer_flatness_relenergy_gate": "0.5",
             "fired_energy_trim": "0", "fired_flatness_gate": "0", "fired_flatness_relenergy_gate": "0"},
        ]
        g = aggregate_by_snr(rows)[0]
        self.assertAlmostEqual(g["tail_sep"], 0.5)            # 1 of 2 sep CERs > 1.0
        self.assertAlmostEqual(g["tail_flatness_gate"], 0.0)  # gate killed the tail


class TestSelectiveGatePolicy(unittest.TestCase):
    def test_guard_routes_to_gate_only_on_degenerate(self) -> None:
        rows = [
            # catastrophic + degenerate (high CR) -> guard should switch to the gate (big win)
            {"cer_sep": "5.0", "cer_flatness_relenergy_gate": "0.8", "cr_sep1": "3.5", "cr_sep2": "1.2"},
            {"cer_sep": "4.0", "cer_flatness_relenergy_gate": "0.7", "cr_sep1": "1.0", "cr_sep2": "3.0"},
            # healthy + non-degenerate (low CR) -> guard should KEEP raw sep (gate would hurt)
            {"cer_sep": "0.4", "cer_flatness_relenergy_gate": "0.9", "cr_sep1": "1.5", "cr_sep2": "1.1"},
            {"cer_sep": "0.5", "cer_flatness_relenergy_gate": "1.0", "cr_sep1": "1.2", "cr_sep2": "1.3"},
        ]
        out = selective_gate_policy(rows, threshold=2.4)
        self.assertEqual(out["n"], 4)
        self.assertAlmostEqual(out["guard_fired_frac"], 0.5)              # 2 of 4 degenerate
        # guard_gated = [0.8, 0.7, 0.4, 0.5] -> 0.6 ; beats always_sep (2.475) and always_gate (0.85)
        self.assertAlmostEqual(out["mean_cer"]["guard_gated"], 0.6)
        self.assertLess(out["mean_cer"]["guard_gated"], out["mean_cer"]["always_sep"])
        self.assertLess(out["mean_cer"]["guard_gated"], out["mean_cer"]["always_gate"])
        # guard_gated == oracle here (the guard picks the better arm on every row)
        self.assertAlmostEqual(out["regret_vs_oracle"]["guard_gated"], 0.0)
        self.assertAlmostEqual(out["tail_rate"]["guard_gated"], 0.0)
        self.assertAlmostEqual(out["tail_rate"]["always_sep"], 0.5)

    def test_skips_rows_missing_signals(self) -> None:
        rows = [{"cer_sep": "1.0", "cer_flatness_relenergy_gate": "0.5", "cr_sep1": "", "cr_sep2": ""}]
        self.assertEqual(selective_gate_policy(rows)["n"], 0)


if __name__ == "__main__":
    unittest.main()
