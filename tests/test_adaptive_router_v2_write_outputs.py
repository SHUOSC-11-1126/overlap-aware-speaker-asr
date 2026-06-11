from __future__ import annotations

import csv
import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from src.adaptive_router_v2 import render_gold_md, write_csv_json


class AdaptiveRouterV2WriteOutputsTest(unittest.TestCase):
    def test_write_csv_json_writes_matching_csv_and_json_payloads(self) -> None:
        rows = [
            {
                "strategy": "fixed_mixed_whisper",
                "average_cer": 0.2,
                "sample_count": 5,
            }
        ]
        fieldnames = ["strategy", "average_cer", "sample_count"]
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "performance.csv"
            json_path = Path(tmp_dir) / "performance.json"
            write_csv_json(rows, csv_path, json_path, fieldnames)
            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                loaded_csv = list(csv.DictReader(handle))
            loaded_json = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(loaded_csv[0]["strategy"], "fixed_mixed_whisper")
        self.assertEqual(loaded_csv[0]["average_cer"], "0.2")
        self.assertEqual(loaded_csv[0]["sample_count"], "5")
        self.assertEqual(loaded_json, rows)

    def test_render_gold_md_writes_expected_strategy_table(self) -> None:
        performance_rows = [
            {"strategy": name, "average_cer": 0.1, "sample_count": 5}
            for name in [
                "fixed_mixed_whisper",
                "fixed_separated_whisper",
                "fixed_separated_whisper_cleaned",
                "oracle_best",
                "rule_router_v1",
                "feature_router_v2",
            ]
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            figures_dir = root / "results" / "figures"
            figures_dir.mkdir(parents=True)
            with unittest.mock.patch("src.adaptive_router_v2.PROJECT_ROOT", root):
                md_path = render_gold_md(performance_rows)
            content = md_path.read_text(encoding="utf-8")
        self.assertIn("# Feature Router v2 Performance", content)
        self.assertIn("fixed_mixed_whisper", content)
        self.assertIn("feature_router_v2", content)


if __name__ == "__main__":
    unittest.main()
