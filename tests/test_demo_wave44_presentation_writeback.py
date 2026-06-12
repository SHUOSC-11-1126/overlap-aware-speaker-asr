from __future__ import annotations

import unittest
from unittest.mock import patch

from src.demo_wave44_presentation_writeback import (
    build_extended_polish_rows,
    build_fill_row,
    run_wave44_presentation_writeback,
)


class DemoWave44PresentationWritebackTest(unittest.TestCase):
    def test_build_extended_polish_rows_includes_wave44(self) -> None:
        rows = build_extended_polish_rows()
        self.assertIn("frontier_wave44", {row["section_id"] for row in rows})
        self.assertEqual(len(rows), 45)

    def test_build_fill_row_records_wave44_status(self) -> None:
        row = build_fill_row(build_extended_polish_rows())
        self.assertEqual(row["storyboard_receipt_status"], "wave44_presentation_extension_complete")

    def test_run_wave44_presentation_writeback_requires_wave44_closure(self) -> None:
        with patch(
            "src.demo_wave44_presentation_writeback.load_json_dict",
            side_effect=[
                {"execution_status": "pending"},
                {
                    "fill_status": "writeback_filled",
                    "storyboard_receipt_status": "wave43_presentation_extension_complete",
                },
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_wave44_presentation_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
