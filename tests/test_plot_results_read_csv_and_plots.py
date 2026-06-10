from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from src.plot_results import plot_cer_by_case, plot_cer_by_method_average, read_csv_rows


class PlotResultsReadCsvAndPlotsTest(unittest.TestCase):
    def test_read_csv_rows_loads_cer_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "cer_results.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["case_id", "method", "cer"])
                writer.writeheader()
                writer.writerow(
                    {"case_id": "NoOverlap", "method": "mixed_whisper", "cer": "0.21"}
                )
            rows = read_csv_rows(csv_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["case_id"], "NoOverlap")

    def test_read_csv_rows_raises_for_missing_file(self) -> None:
        from src.config import PROJECT_ROOT

        missing = PROJECT_ROOT / "results" / "tables" / "__missing_plot_results__.csv"
        with self.assertRaises(FileNotFoundError):
            read_csv_rows(missing)

    def test_plot_cer_by_case_writes_png(self) -> None:
        grouped = {
            "NoOverlap": {"mixed_whisper": 0.21, "separated_whisper": 0.05},
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "cer_by_case.png"
            plot_cer_by_case(grouped, out_path)
            self.assertTrue(out_path.is_file())
            self.assertGreater(out_path.stat().st_size, 0)

    def test_plot_cer_by_method_average_returns_averages(self) -> None:
        grouped = {
            "NoOverlap": {"mixed_whisper": 0.20, "separated_whisper": 0.10},
            "LightOverlap": {"mixed_whisper": 0.30, "separated_whisper": 0.40},
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "cer_by_method_average.png"
            averages = plot_cer_by_method_average(grouped, out_path)
            self.assertAlmostEqual(averages["mixed_whisper"], 0.25)
            self.assertAlmostEqual(averages["separated_whisper"], 0.25)
            self.assertTrue(out_path.is_file())


if __name__ == "__main__":
    unittest.main()
