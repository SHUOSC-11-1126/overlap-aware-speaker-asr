from __future__ import annotations

import unittest
from unittest.mock import patch

from src.demo_wave5_presentation_writeback import (
    build_extended_polish_rows,
    build_fill_row,
    run_wave5_presentation_writeback,
)


class DemoWave5PresentationWritebackTest(unittest.TestCase):
    def test_build_extended_polish_rows_includes_wave5(self) -> None:
        rows = build_extended_polish_rows()
        section_ids = {row["section_id"] for row in rows}
        self.assertIn("frontier_wave5", section_ids)
        self.assertEqual(len(rows), 6)

    def test_build_fill_row_records_wave5_receipt_status(self) -> None:
        row = build_fill_row(build_extended_polish_rows())
        self.assertEqual(row["storyboard_receipt_status"], "wave5_presentation_extension_complete")
        self.assertEqual(row["polish_section_count"], "6")

    def test_run_wave5_presentation_writeback_requires_phase_coordination(self) -> None:
        with patch(
            "src.demo_wave5_presentation_writeback.load_json_dict",
            side_effect=[
                {"execution_status": "pending"},
                {"overall_state": "presentation_polish_complete"},
                {"fill_status": "writeback_filled"},
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_wave5_presentation_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
