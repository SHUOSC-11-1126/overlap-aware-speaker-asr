from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.config import load_config
from src.plot_results import build_adaptive_rows, ensure_dir, grouped_cer_rows, to_float


class PlotResultsHelpersTest(unittest.TestCase):
    def test_to_float_parses_numeric_strings(self) -> None:
        self.assertEqual(to_float("0.25"), 0.25)
        self.assertEqual(to_float(None), 0.0)

    def test_to_float_returns_zero_for_invalid_input(self) -> None:
        self.assertEqual(to_float("not-a-number"), 0.0)

    def test_grouped_cer_rows_groups_by_case_and_method(self) -> None:
        grouped = grouped_cer_rows(
            [
                {"case_id": "NoOverlap", "method": "mixed_whisper", "cer": "0.21"},
                {"case_id": "NoOverlap", "method": "separated_whisper", "cer": "0.05"},
            ]
        )
        self.assertEqual(grouped["NoOverlap"]["mixed_whisper"], 0.21)
        self.assertEqual(grouped["NoOverlap"]["separated_whisper"], 0.05)

    def test_ensure_dir_creates_missing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "nested" / "tables"
            ensure_dir(target)
            self.assertTrue(target.is_dir())

    def test_build_adaptive_rows_selects_lowest_cer_method(self) -> None:
        grouped = {
            "NoOverlap": {
                "mixed_whisper": 0.21,
                "separated_whisper": 0.05,
            }
        }
        rows = build_adaptive_rows(grouped, load_config())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["best_method"], "separated_whisper")
        self.assertEqual(rows[0]["best_cer"], 0.05)


if __name__ == "__main__":
    unittest.main()
