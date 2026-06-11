from __future__ import annotations

import csv
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from src.router_feature_importance import compute_feature_importance


class RouterFeatureImportanceAblationTest(unittest.TestCase):
    def test_compute_feature_importance_derives_scores_from_ablation_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            tables_dir = root / "results" / "tables"
            tables_dir.mkdir(parents=True)
            ablation_path = tables_dir / "router_ablation_results.csv"
            rows = [
                {"ablation_group": "baseline_v2", "average_cer": "0.20"},
                {"ablation_group": "ablation_text_length_ratio", "average_cer": "0.30"},
                {"ablation_group": "ablation_duplicate_removed_count", "average_cer": "0.25"},
            ]
            with ablation_path.open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.DictWriter(handle, fieldnames=["ablation_group", "average_cer"])
                writer.writeheader()
                writer.writerows(rows)
            with unittest.mock.patch("src.router_feature_importance.PROJECT_ROOT", root):
                importance_rows = compute_feature_importance()
        feature_names = {row["feature_name"] for row in importance_rows}
        self.assertIn("text_length_ratio", feature_names)
        self.assertIn("duplicate_removed_count", feature_names)
        for row in importance_rows:
            self.assertGreater(float(row["importance_score"]), 0.0)


if __name__ == "__main__":
    unittest.main()
