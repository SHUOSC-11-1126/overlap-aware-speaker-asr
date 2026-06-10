from __future__ import annotations

import unittest

from src.plot_results import grouped_cer_rows, to_float


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


if __name__ == "__main__":
    unittest.main()
