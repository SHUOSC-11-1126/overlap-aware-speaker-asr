from __future__ import annotations

import unittest

import numpy as np

from src.speaker_similarity_probe import (
    correlate,
    cosine_sim,
    mel_filterbank,
    mfcc_embedding,
    per_pair_benefit,
)


class TestMfccEmbedding(unittest.TestCase):
    def test_embedding_shape_and_finite(self) -> None:
        t = np.linspace(0, 1, 16000, endpoint=False)
        sig = np.sin(2 * np.pi * 220 * t).astype(np.float32)
        emb = mfcc_embedding(sig, n_mfcc=13)
        self.assertIsNotNone(emb)
        assert emb is not None
        self.assertEqual(emb.shape[0], 26)  # mean(13) + std(13)
        self.assertTrue(np.all(np.isfinite(emb)))
        self.assertAlmostEqual(float(np.linalg.norm(emb)), 1.0, places=5)  # L2-normalized

    def test_too_short_returns_none(self) -> None:
        self.assertIsNone(mfcc_embedding(np.zeros(100, dtype=np.float32), frame=400))

    def test_distinct_tones_less_similar_than_identical(self) -> None:
        t = np.linspace(0, 1, 16000, endpoint=False)
        a = mfcc_embedding(np.sin(2 * np.pi * 180 * t).astype(np.float32))
        a2 = mfcc_embedding(np.sin(2 * np.pi * 180 * t).astype(np.float32))
        b = mfcc_embedding(np.sin(2 * np.pi * 900 * t).astype(np.float32))
        assert a is not None and a2 is not None and b is not None
        self.assertGreater(cosine_sim(a, a2), cosine_sim(a, b))


class TestMelFilterbank(unittest.TestCase):
    def test_shape(self) -> None:
        fb = mel_filterbank(16000, 400, 26)
        self.assertEqual(fb.shape, (26, 201))
        self.assertTrue(np.all(fb >= 0))


class TestPerPairBenefit(unittest.TestCase):
    def test_mean_median_capped(self) -> None:
        rows = [
            {"config": "greedy", "con": "con_1.wav", "pro": "pro_1.wav", "delta_cer": "0.1"},
            {"config": "greedy", "con": "con_1.wav", "pro": "pro_1.wav", "delta_cer": "0.3"},
            {"config": "greedy", "con": "con_1.wav", "pro": "pro_1.wav", "delta_cer": "5.0"},  # tail
            {"config": "fallback", "con": "con_1.wav", "pro": "pro_1.wav", "delta_cer": "9.0"},  # ignored
        ]
        b = per_pair_benefit(rows)["con_1.wav", "pro_1.wav"]
        self.assertAlmostEqual(b["mean"], (0.1 + 0.3 + 5.0) / 3)  # tail inflates mean
        self.assertAlmostEqual(b["median"], 0.3)  # tail-robust
        self.assertAlmostEqual(b["capped"], (0.1 + 0.3 + 1.0) / 3)  # 5.0 -> 1.0


class TestCorrelateDemonstratesTailConfound(unittest.TestCase):
    def test_mean_corr_inflated_by_tail_median_is_clean(self) -> None:
        # dissimilarity unrelated to the true (median) benefit, but one high-dissim point
        # has a catastrophic tail that inflates its MEAN benefit -> spurious mean correlation.
        dis = [0.01, 0.02, 0.03, 0.20]
        median_benefit = [0.10, 0.12, 0.08, 0.11]  # flat: no real relationship
        mean_benefit = [0.10, 0.12, 0.08, 3.00]    # tail on the high-dissim point
        c_med = correlate(dis, median_benefit)
        c_mean = correlate(dis, mean_benefit)
        self.assertLess(abs(c_med["pearson"]), 0.5)        # robust: weak
        self.assertGreater(c_mean["pearson"], c_med["pearson"])  # mean inflated by the tail


if __name__ == "__main__":
    unittest.main()
