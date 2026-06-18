"""Tests for the offline prosody/emotion feature library (experimental/frontier).

These pin the PURE, label-free acoustic emotion proxies the emotion frontier rests on. The headline
property under test: `prosody_distance(..., energy_invariant=True)` must be GAIN-invariant — scaling a
signal's amplitude must NOT register as emotional change (it shows up only in the separate
`gain_component`). That is the confound control the whole "emotional separation tax" study depends on.
All tests use short synthetic signals so they run offline in well under a second without pyin flakiness.
"""
from __future__ import annotations

import unittest

import numpy as np

from src.prosody import arousal_index, prosodic_features, prosody_distance

SR = 16000


def _sine(freq: float, dur: float = 0.6, amp: float = 0.3, sr: int = SR) -> np.ndarray:
    t = np.arange(int(dur * sr), dtype=np.float32) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _am_sine(freq: float, mod: float = 4.0, dur: float = 0.6, amp: float = 0.3, sr: int = SR) -> np.ndarray:
    """Amplitude-modulated sine: same mean energy band but large RMS dynamics (an arousal cue)."""
    t = np.arange(int(dur * sr), dtype=np.float32) / sr
    env = 0.5 * (1.0 + np.sin(2 * np.pi * mod * t))
    return (amp * env * np.sin(2 * np.pi * freq * t)).astype(np.float32)


class TestProsodicFeatures(unittest.TestCase):
    def test_returns_expected_keys(self) -> None:
        feat = prosodic_features(_sine(150.0))
        for k in ("f0_median", "f0_iqr", "voiced_frac", "rms_mean", "rms_dyn_db",
                  "centroid_mean", "centroid_std", "rolloff_mean", "bandwidth_mean", "zcr_mean"):
            self.assertIn(k, feat)
            self.assertTrue(np.isfinite(feat[k]), f"{k} not finite")

    def test_f0_tracks_pitch(self) -> None:
        lo = prosodic_features(_sine(120.0))
        hi = prosodic_features(_sine(260.0))
        self.assertLess(lo["f0_median"], hi["f0_median"])

    def test_centroid_tracks_brightness(self) -> None:
        lo = prosodic_features(_sine(120.0))
        hi = prosodic_features(_sine(300.0))
        self.assertLess(lo["centroid_mean"], hi["centroid_mean"])

    def test_empty_or_silent_is_safe(self) -> None:
        feat = prosodic_features(np.zeros(8000, dtype=np.float32))
        self.assertTrue(all(np.isfinite(v) for v in feat.values()))
        self.assertEqual(feat["voiced_frac"], 0.0)


class TestEnergyInvariance(unittest.TestCase):
    """The core confound control: amplitude scaling is NOT emotional change."""

    def test_gain_does_not_move_emotional_distortion(self) -> None:
        x = _sine(180.0, amp=0.3)
        loud = (x * 4.0).astype(np.float32)
        fa, fb = prosodic_features(x), prosodic_features(loud)
        d = prosody_distance(fa, fb, energy_invariant=True)
        # pure gain: emotional distortion ~0, but the gain component is large and reported separately
        self.assertLess(d["emotional_distortion"], 0.05)
        self.assertGreater(d["gain_component_db"], 6.0)

    def test_pitch_change_moves_emotional_distortion(self) -> None:
        d = prosody_distance(prosodic_features(_sine(120.0)), prosodic_features(_sine(280.0)),
                             energy_invariant=True)
        self.assertGreater(d["emotional_distortion"], 0.1)

    def test_distance_is_zero_to_self(self) -> None:
        f = prosodic_features(_sine(200.0))
        d = prosody_distance(f, f, energy_invariant=True)
        self.assertAlmostEqual(d["emotional_distortion"], 0.0, places=6)
        self.assertAlmostEqual(d["arousal_distance"], 0.0, places=6)


class TestArousalIndex(unittest.TestCase):
    def test_amplitude_dynamics_raise_arousal(self) -> None:
        steady = arousal_index(prosodic_features(_sine(200.0)))
        dynamic = arousal_index(prosodic_features(_am_sine(200.0)))
        self.assertGreater(dynamic, steady)

    def test_arousal_is_finite(self) -> None:
        self.assertTrue(np.isfinite(arousal_index(prosodic_features(_sine(150.0)))))


if __name__ == "__main__":
    unittest.main()
