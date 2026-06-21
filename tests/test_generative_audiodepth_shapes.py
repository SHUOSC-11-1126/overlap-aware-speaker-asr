from __future__ import annotations

import unittest

import numpy as np

from src.build_promptable_acoustic_map_dataset import build_rows
from src.generative_audiodepth_common import MAP_TASKS, load_npy, unique_samples
from src.generative_audiodepth_models import build_promptable_prototype


class GenerativeAudioDepthShapeTest(unittest.TestCase):
    def test_promptable_map_shapes(self) -> None:
        rows, _, _ = build_rows(limit=3)
        samples = unique_samples(rows)
        model = build_promptable_prototype(samples, rows, load_npy)
        sample = samples[0]
        for task in MAP_TASKS:
            pred = model.predict(sample, task)
            self.assertEqual(pred.shape, (64, 96))
            self.assertTrue(np.isfinite(pred).all())

    def test_vector_task_shapes(self) -> None:
        rows, _, _ = build_rows(limit=3)
        samples = unique_samples(rows)
        model = build_promptable_prototype(samples, rows, load_npy)
        self.assertEqual(model.predict(samples[0], "ROUTE_REGRET").shape, (3,))
        self.assertEqual(model.predict(samples[0], "REVIEW_RISK").shape, (3,))


if __name__ == "__main__":
    unittest.main()
