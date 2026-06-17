"""Tests for the speaker-conditioned gate (experimental/frontier).

The gate's job: where the spectral-flatness gate fails (babble noise, whose residual is
speech-like and spectrally indistinguishable from the target), use a speaker embedding to keep
windows that match the track's dominant speaker and crop windows that don't. These tests lock
the PURE logic with an injected fake embedder, so they run without resemblyzer installed.
"""
from __future__ import annotations

import unittest

import numpy as np

from src.speaker_conditioned_gate import (
    cosine_sims,
    frame_windows,
    keep_span_from_sims,
    reference_embedding,
    speaker_gate_trim,
    window_energies,
)


def _tone(n: int, freq: float = 220.0, amp: float = 0.3) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / 16000.0
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _noise(n: int, amp: float, seed: int) -> np.ndarray:
    return (amp * np.random.default_rng(seed).standard_normal(n)).astype(np.float32)


# Fake embedder: a "speaker id" vector decided by window energy (loud target vs quiet residual).
def _fake_embed(w: np.ndarray) -> np.ndarray:
    return np.array([1.0, 0.0]) if float(np.mean(np.asarray(w) ** 2)) > 0.01 else np.array([0.0, 1.0])


class TestFrameWindows(unittest.TestCase):
    def test_counts(self) -> None:
        w = frame_windows(10000, win=4000, hop=2000)
        self.assertEqual(w[0], (0, 4000))
        self.assertTrue(all(e - s == 4000 for s, e in w))
        self.assertTrue(all(w[i + 1][0] - w[i][0] == 2000 for i in range(len(w) - 1)))

    def test_too_short(self) -> None:
        self.assertEqual(frame_windows(100, win=4000, hop=2000), [])


class TestWindowEnergiesAndRef(unittest.TestCase):
    def test_window_energies(self) -> None:
        x = np.concatenate([np.zeros(4000, np.float32), _tone(4000)])
        e = window_energies(x, [(0, 4000), (4000, 8000)])
        self.assertLess(e[0], e[1])

    def test_reference_embedding_uses_top_energy(self) -> None:
        embs = np.array([[0.0, 1.0], [0.0, 1.0], [1.0, 0.0], [1.0, 0.0]])
        ens = np.array([0.001, 0.001, 0.05, 0.05])  # last two are the loud (target) windows
        ref = reference_embedding(embs, ens, top_frac=0.5)
        self.assertGreater(ref[0], ref[1])  # points to the target embedding [1,0]


class TestCosineSims(unittest.TestCase):
    def test_known(self) -> None:
        embs = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
        sims = cosine_sims(embs, np.array([1.0, 0.0]))
        self.assertAlmostEqual(sims[0], 1.0, places=5)
        self.assertAlmostEqual(sims[1], 0.0, places=5)
        self.assertAlmostEqual(sims[2], 1 / np.sqrt(2), places=5)


class TestKeepSpan(unittest.TestCase):
    def test_contiguous_high_sim_span(self) -> None:
        sims = np.array([0.1, 0.2, 0.9, 0.95, 0.3, 0.92, 0.1])
        self.assertEqual(keep_span_from_sims(sims, 0.5), (2, 6))

    def test_none_high(self) -> None:
        self.assertEqual(keep_span_from_sims(np.array([0.1, 0.2, 0.3]), 0.5), (0, 0))


class TestSpeakerGateTrim(unittest.TestCase):
    def _track(self, seed: int) -> np.ndarray:
        # [quiet noise (babble) | loud tone (target) | quiet noise (babble)]
        n = 16000
        return np.concatenate([_noise(n, 0.02, seed), _tone(n), _noise(n, 0.02, seed + 1)]).astype(np.float32)

    def test_crops_to_target(self) -> None:
        track = self._track(1)
        out = speaker_gate_trim(track, _fake_embed, win=4000, hop=2000, margin_samples=2000, min_gap=0.1)
        self.assertLess(len(out), len(track))           # cropped the babble ends
        self.assertGreater(len(out), 16000 - 4000)      # kept ~the target region

    def test_all_target_unchanged(self) -> None:
        track = _tone(3 * 16000)                          # all target -> sims uniformly high -> abstain
        out = speaker_gate_trim(track, _fake_embed, win=4000, hop=2000, margin_samples=2000, min_gap=0.1)
        self.assertEqual(len(out), len(track))

    def test_short_unchanged(self) -> None:
        short = _tone(3000)
        self.assertTrue(np.array_equal(
            speaker_gate_trim(short, _fake_embed, win=4000, hop=2000), short))

    def test_deterministic(self) -> None:
        track = self._track(2)
        a = speaker_gate_trim(track, _fake_embed, win=4000, hop=2000, min_gap=0.1)
        b = speaker_gate_trim(track, _fake_embed, win=4000, hop=2000, min_gap=0.1)
        self.assertTrue(np.array_equal(a, b))


if __name__ == "__main__":
    unittest.main()
