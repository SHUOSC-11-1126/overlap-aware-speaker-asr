from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.plot_results import update_summary_md


class PlotResultsUpdateSummaryMdTest(unittest.TestCase):
    def test_update_summary_md_writes_average_cer_and_case_table(self) -> None:
        averages = {
            "mixed_whisper": 0.2,
            "separated_whisper": 0.05,
            "separated_whisper_cleaned": 0.09,
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            table_dir = root / "results" / "tables"
            (root / "results" / "figures").mkdir(parents=True)
            table_dir.mkdir(parents=True)
            csv_path = table_dir / "adaptive_routing_results.csv"
            with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["case_id", "best_method", "best_cer"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "case_id": "FixtureCase",
                        "best_method": "separated_whisper",
                        "best_cer": "0.05",
                    }
                )

            with patch("src.plot_results.PROJECT_ROOT", root):
                md_path = update_summary_md(averages, adaptive_best_average=0.05)

            markdown = md_path.read_text(encoding="utf-8")
            self.assertIn("Mixed average: 0.200000", markdown)
            self.assertIn("Adaptive best average: 0.050000", markdown)
            self.assertIn("FixtureCase", markdown)


if __name__ == "__main__":
    unittest.main()
