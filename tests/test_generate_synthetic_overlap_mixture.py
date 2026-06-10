from __future__ import annotations

import unittest

import numpy as np

from src.generate_synthetic_overlap import TARGET_SR, AudioClip, build_mixture


class GenerateSyntheticOverlapMixtureTest(unittest.TestCase):
    def test_build_mixture_with_zero_overlap_inserts_gap(self) -> None:
        spk1 = AudioClip("a.wav", np.full(1000, 0.2, dtype=np.float32), TARGET_SR)
        spk2 = AudioClip("b.wav", np.full(500, 0.1, dtype=np.float32), TARGET_SR)
        mixed, track1, track2, scale = build_mixture(spk1, spk2, overlap_ratio=0.0, gap_sec=0.1)
        self.assertAlmostEqual(scale, 0.95)
        gap_samples = int(round(0.1 * TARGET_SR))
        self.assertGreater(np.argmax(track2 > 0), len(spk1.samples) + gap_samples - 1)
        self.assertTrue(np.allclose(mixed, track1 + track2))

    def test_build_mixture_with_overlap_aligns_tracks(self) -> None:
        spk1 = AudioClip("a.wav", np.full(1000, 0.2, dtype=np.float32), TARGET_SR)
        spk2 = AudioClip("b.wav", np.full(1000, 0.2, dtype=np.float32), TARGET_SR)
        mixed, track1, track2, _ = build_mixture(spk1, spk2, overlap_ratio=0.5)
        self.assertEqual(len(mixed), 1500)
        self.assertTrue(np.allclose(mixed, track1 + track2))


if __name__ == "__main__":
    unittest.main()
