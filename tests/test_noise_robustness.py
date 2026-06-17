from __future__ import annotations

import unittest

import numpy as np

from src.noise_robustness import (
    add_noise,
    aggregate_grid,
    measured_snr_db,
    speech_power,
)


class TestAddNoise(unittest.TestCase):
    def setUp(self) -> None:
        t = np.linspace(0, 1, 16000, endpoint=False)
        self.sig = (0.3 * np.sin(2 * np.pi * 200 * t)).astype(np.float32)

    def test_clean_passthrough(self) -> None:
        out = add_noise(self.sig, None, seed=0)
        self.assertTrue(np.allclose(out, self.sig))

    def test_target_snr_achieved(self) -> None:
        for target in (20.0, 10.0, 0.0):
            noisy = add_noise(self.sig, target, seed=1)
            meas = measured_snr_db(self.sig, noisy)
            self.assertAlmostEqual(meas, target, delta=1.0)  # within 1 dB

    def test_lower_snr_more_noise(self) -> None:
        n20 = add_noise(self.sig, 20.0, seed=2)
        n0 = add_noise(self.sig, 0.0, seed=2)
        self.assertGreater(float(np.mean((n0 - self.sig) ** 2)), float(np.mean((n20 - self.sig) ** 2)))

    def test_deterministic_seed(self) -> None:
        self.assertTrue(np.array_equal(add_noise(self.sig, 10.0, 7), add_noise(self.sig, 10.0, 7)))

    def test_no_clipping(self) -> None:
        self.assertLessEqual(float(np.max(np.abs(add_noise(self.sig, 0.0, seed=3)))), 0.98 + 1e-6)


class TestSpeechPower(unittest.TestCase):
    def test_uses_speech_region(self) -> None:
        x = np.zeros(8000, dtype=np.float32)
        x[2000:3000] = 0.5  # loud region
        # power over speech region (0.25) >> power over whole clip
        self.assertGreater(speech_power(x), 0.1)


class TestAggregateGrid(unittest.TestCase):
    def test_grid_per_snr_and_trim_gain(self) -> None:
        rows = [
            {"snr_db": "None", "cer_mixed": "0.5", "cer_sep": "0.3", "cer_sep_trim": "0.2"},
            {"snr_db": "None", "cer_mixed": "0.6", "cer_sep": "5.0", "cer_sep_trim": "0.3"},  # sep tail
            {"snr_db": "0.0", "cer_mixed": "0.7", "cer_sep": "0.9", "cer_sep_trim": "0.9"},
        ]
        grid = {str(g["snr_db"]): g for g in aggregate_grid(rows)}
        clean = grid["clean"]
        self.assertEqual(clean["n"], 2)
        self.assertAlmostEqual(clean["mean_cer_sep"], (0.3 + 5.0) / 2)
        self.assertAlmostEqual(clean["mean_cer_sep_trim"], (0.2 + 0.3) / 2)
        self.assertGreater(clean["trim_gain_vs_sep"], 0)  # trim helps when sep has a tail
        self.assertAlmostEqual(clean["tail_rate_sep"], 0.5)
        self.assertAlmostEqual(clean["tail_rate_sep_trim"], 0.0)
        # at 0 dB, trim gives no gain here
        self.assertAlmostEqual(grid["0.0"]["trim_gain_vs_sep"], 0.0)


if __name__ == "__main__":
    unittest.main()
