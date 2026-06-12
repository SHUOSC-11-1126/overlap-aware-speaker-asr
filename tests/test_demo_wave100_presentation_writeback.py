from __future__ import annotations

import unittest
from unittest.mock import patch

from src.demo_wave100_presentation_writeback import (
    build_extended_polish_rows,
    build_fill_row,
    run_wave100_presentation_writeback,
)


class DemoWave100PresentationWritebackTest(unittest.TestCase):
    def test_build_extended_polish_rows_includes_wave100(self) -> None:
        rows = build_extended_polish_rows()
        self.assertTrue(any(row["section_id"] == "frontier_wave100" for row in rows))
        self.assertEqual(len(rows), 101)

    def test_build_fill_row_records_wave100_status(self) -> None:
        rows = build_extended_polish_rows()
        row = build_fill_row(rows)
        self.assertEqual(row["storyboard_receipt_status"], "wave100_presentation_extension_complete")
        self.assertEqual(row["polish_section_count"], "101")

    def test_run_wave100_presentation_writeback_requires_wave100_closure(self) -> None:
        with patch(
            "src.demo_wave100_presentation_writeback.load_json_dict",
            side_effect=[
                {"execution_status": "pending"},
                {
                    "fill_status": "writeback_filled",
                    "storyboard_receipt_status": "wave99_presentation_extension_complete",
                },
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_wave100_presentation_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
