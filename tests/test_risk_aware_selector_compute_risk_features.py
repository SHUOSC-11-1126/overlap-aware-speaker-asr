from __future__ import annotations

import unittest

from src.risk_aware_selector import compute_risk_features


class RiskAwareSelectorComputeRiskFeaturesTest(unittest.TestCase):
    def test_compute_risk_features_derives_stability_signals_for_no_overlap(self) -> None:
        v2_row = {"selected_method": "separated_whisper", "overlap_level": 0}
        v1_row = {"selected_method": "separated_whisper"}
        features = compute_risk_features("NoOverlap", v2_row, v1_row)

        self.assertEqual(features["base_v2_method"], "separated_whisper")
        self.assertEqual(features["base_v1_method"], "separated_whisper")
        self.assertGreater(features["text_length_ratio"], 0.0)
        self.assertIn("mixed_text", features)
        self.assertIn("separated_text", features)
        self.assertGreaterEqual(features["method_disagreement_score"], 0.0)


if __name__ == "__main__":
    unittest.main()
