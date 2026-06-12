from __future__ import annotations

import unittest
from unittest.mock import patch

from src.demo_wave6_presentation_writeback import (
    build_extended_polish_rows,
    build_fill_row,
    run_wave6_presentation_writeback,
)


class DemoWave6PresentationWritebackTest(unittest.TestCase):
    def test_build_extended_polish_rows_includes_wave6(self) -> None:
        rows = build_extended_polish_rows()
        self.assertIn("frontier_wave6", {row["section_id"] for row in rows})
        self.assertEqual(len(rows), 7)

    def test_build_fill_row_records_wave6_status(self) -> None:
        row = build_fill_row(build_extended_polish_rows())
        self.assertEqual(row["storyboard_receipt_status"], "wave6_presentation_extension_complete")
        self.assertEqual(row["blocker"], "controlled_benchmark_timing_pending")

    def test_run_wave6_presentation_writeback_requires_benchmark_coordination(self) -> None:
        with patch(
            "src.demo_wave6_presentation_writeback.load_json_dict",
            side_effect=[
                {"execution_status": "pending"},
                {"overall_state": "presentation_wave5_extension_complete"},
                {"fill_status": "writeback_filled"},
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_wave6_presentation_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
