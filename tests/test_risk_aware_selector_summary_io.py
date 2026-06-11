from __future__ import annotations

import csv
import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from src.risk_aware_selector import render_summary, write_csv_json


class RiskAwareSelectorSummaryIoTest(unittest.TestCase):
    def test_write_csv_json_writes_matching_csv_and_json_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            csv_path = base / "selection.csv"
            json_path = base / "selection.json"
            rows = [
                {
                    "case_id": "NoOverlap",
                    "final_selected_method": "separated_whisper",
                    "risk_level": "low",
                    "risk_reasons": "stable",
                }
            ]
            fieldnames = ["case_id", "final_selected_method", "risk_level", "risk_reasons"]
            write_csv_json(rows, csv_path, json_path, fieldnames)

            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                loaded = list(csv.DictReader(handle))
            self.assertEqual(loaded[0]["case_id"], "NoOverlap")
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))[0]["risk_level"], "low")

    def test_render_summary_writes_selection_and_performance_tables(self) -> None:
        rows = [
            {
                "case_id": "NoOverlap",
                "final_selected_method": "separated_whisper",
                "risk_level": "low",
                "risk_reasons": "stable",
            }
        ]
        performance = [
            {"strategy": strategy, "average_cer": 0.1}
            for strategy in [
                "fixed_mixed_whisper",
                "fixed_separated_whisper",
                "fixed_separated_whisper_cleaned",
                "router_v1",
                "router_v2",
                "risk_aware_selector",
                "oracle_best",
            ]
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "results" / "figures").mkdir(parents=True, exist_ok=True)
            output_path = root / "results" / "figures" / "risk_aware_selection_summary.md"
            with unittest.mock.patch("src.risk_aware_selector.PROJECT_ROOT", root):
                result = render_summary(rows, performance, manual_review_count=0, coverage=1.0)
            self.assertEqual(result, output_path)
            summary = output_path.read_text(encoding="utf-8")
            self.assertIn("Risk-Aware Final Selector Summary", summary)
            self.assertIn("NoOverlap", summary)
            self.assertIn("risk_aware_selector", summary)


if __name__ == "__main__":
    unittest.main()
