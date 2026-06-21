import unittest

from src.generative_audiodepth_reliability_common import pairwise_rank_accuracy, route_from_regrets
from src.train_generative_regret_ranker import rank_adjust


class GenerativeRegretRankingTest(unittest.TestCase):
    def test_pairwise_rank_accuracy(self):
        truth = [[0.0, 0.3, 0.4], [0.2, 0.0, 0.3]]
        pred = [[0.0, 0.2, 0.5], [0.3, 0.0, 0.4]]
        self.assertEqual(pairwise_rank_accuracy(truth, pred), 1.0)

    def test_rank_adjust_penalizes_high_error_mixed(self):
        row = {
            "mixed_cer": "0.9",
            "overlap_proxy_mean": "0.5",
            "uncertainty_proxy_mean": "0.4",
            "route_gap": "0.1",
            "review_needed": "False",
        }
        adjusted, risk = rank_adjust([0.0, 0.1, 0.2], row, use_review=True)
        self.assertGreater(adjusted[0], 0.0)
        self.assertGreaterEqual(risk, 0.0)
        self.assertIn(route_from_regrets(adjusted), {"mixed", "separated", "cleaned"})


if __name__ == "__main__":
    unittest.main()
