from __future__ import annotations

import unittest
from unittest.mock import patch

from src.demo_wave57_presentation_writeback import (
    build_extended_polish_rows,
    build_fill_row,
    run_wave57_presentation_writeback,
)


class DemoWave57PresentationWritebackTest(unittest.TestCase):
    def test_build_extended_polish_rows_includes_wave57(self) -> None:
        rows = build_extended_polish_rows()
        self.assertTrue(any(row["section_id"] == "frontier_wave57" for row in rows))
        self.assertEqual(len(rows), 58)

    def test_build_fill_row_records_wave57_status(self) -> None:
        rows = build_extended_polish_rows()
        row = build_fill_row(rows)
        self.assertEqual(row["storyboard_receipt_status"], "wave57_presentation_extension_complete")
        self.assertEqual(row["polish_section_count"], "58")

    def test_run_wave57_presentation_writeback_requires_wave57_closure(self) -> None:
        with patch(
            "src.demo_wave57_presentation_writeback.load_json_dict",
            side_effect=[
                {"execution_status": "pending"},
                {
                    "fill_status": "writeback_filled",
                    "storyboard_receipt_status": "wave56_presentation_extension_complete",
                },
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_wave57_presentation_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
