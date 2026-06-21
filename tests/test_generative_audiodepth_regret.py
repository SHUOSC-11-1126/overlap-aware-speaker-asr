from __future__ import annotations

import unittest

import numpy as np

from src.generative_audiodepth_models import select_route_from_regret
from src.generative_audiodepth_losses import pairwise_ranking_loss, smooth_l1


class GenerativeAudioDepthRegretTest(unittest.TestCase):
    def test_select_route_from_regret_prefers_lowest_regret(self) -> None:
        self.assertEqual(select_route_from_regret(np.asarray([0.3, 0.0, 0.1])), "separated")

    def test_cost_weight_can_break_near_tie_toward_mixed(self) -> None:
        self.assertEqual(select_route_from_regret(np.asarray([0.0, 0.01, 0.02]), cost_weight=0.05), "mixed")

    def test_regret_losses_are_non_negative(self) -> None:
        self.assertGreaterEqual(smooth_l1(np.asarray([0.0]), np.asarray([1.0])), 0.0)
        self.assertGreaterEqual(pairwise_ranking_loss(np.asarray([0.2, 0.0]), np.asarray([0.0, 0.4])), 0.0)


if __name__ == "__main__":
    unittest.main()
