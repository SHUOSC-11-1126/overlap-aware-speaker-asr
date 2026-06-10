from __future__ import annotations

import unittest

from src.router_feature_importance import compute_feature_importance


class RouterFeatureImportanceComputeTest(unittest.TestCase):
    def test_compute_feature_importance_returns_default_features_without_ablation(self) -> None:
        rows = compute_feature_importance()
        feature_names = {row["feature_name"] for row in rows}
        self.assertIn("overlap_level", feature_names)
        self.assertIn("text_length_ratio", feature_names)
        self.assertGreater(len(rows), 0)

    def test_compute_feature_importance_scores_are_positive(self) -> None:
        rows = compute_feature_importance()
        for row in rows:
            self.assertGreater(float(row["importance_score"]), 0.0)
            self.assertTrue(str(row["interpretation"]).strip())
            self.assertTrue(str(row["feature_category"]).strip())


if __name__ == "__main__":
    unittest.main()
