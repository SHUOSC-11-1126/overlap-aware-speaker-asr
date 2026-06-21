import unittest

from src.calibrate_generative_regret_safety import calibrate
from src.generative_audiodepth_reliability_common import policy_metrics


class GenerativeSafeFusionTest(unittest.TestCase):
    def test_calibration_can_abstain(self):
        samples = [{"sample_id": "s1", "mixed_cer": "0.9", "separated_cer": "0.2", "cleaned_cer": "0.3", "oracle_route": "separated"}]
        preds = {
            "s1": {
                "sample_id": "s1",
                "predicted_route": "mixed",
                "review_risk": "0.9",
                "predicted_mixed_regret": "0.0",
                "predicted_separated_regret": "0.01",
                "predicted_cleaned_regret": "0.02",
            }
        }
        routes = calibrate(samples, preds, 0.02, 0.5, 0.5)
        self.assertEqual(routes["s1"], "review")

    def test_policy_metrics_counts_false_safe(self):
        samples = [{"sample_id": "s1", "mixed_cer": "0.9", "separated_cer": "0.2", "cleaned_cer": "0.3", "oracle_route": "separated"}]
        metrics = policy_metrics(samples, {"s1": "mixed"}, "bad_policy")
        self.assertEqual(metrics["false_safe_count"], 1)


if __name__ == "__main__":
    unittest.main()
