import unittest

import numpy as np

from src.build_generative_audiodepth_counterfactual_suite import shift_map
from src.evaluate_generative_audiodepth_counterfactual_reliability import monotonic_ok, pairwise_order


class GenerativeAudioDepthCounterfactualTest(unittest.TestCase):
    def test_overlap_monotonic_helper(self):
        self.assertTrue(monotonic_ok([0.1, 0.2, 0.3, 0.4], "overlap_sweep"))
        self.assertFalse(monotonic_ok([0.4, 0.1, 0.3, 0.2], "overlap_sweep"))

    def test_pairwise_order_and_shift(self):
        self.assertEqual(pairwise_order([0.1, 0.2, 0.3]), 1.0)
        arr = np.arange(6, dtype=np.float32).reshape(2, 3)
        shifted = shift_map(arr, 1 / 3)
        self.assertEqual(shifted.shape, arr.shape)


if __name__ == "__main__":
    unittest.main()
