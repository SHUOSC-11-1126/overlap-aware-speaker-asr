from __future__ import annotations

import unittest
from unittest.mock import patch

from src.demo_presentation_writeback import build_fill_row, build_polish_rows, run_presentation_writeback


class DemoPresentationWritebackTest(unittest.TestCase):
    def test_build_polish_rows_include_frontier_anchors(self) -> None:
        rows = build_polish_rows()
        section_ids = {row["section_id"] for row in rows}
        self.assertIn("frontier_wave3", section_ids)
        self.assertEqual(rows[0]["result_label"], "qualitative/demo")

    def test_build_fill_row_records_both_receipts(self) -> None:
        row = build_fill_row(build_polish_rows())
        self.assertEqual(row["storyboard_receipt_status"], "presentation_writeback_complete")
        self.assertEqual(row["walkthrough_receipt_status"], "presentation_writeback_complete")

    def test_run_presentation_writeback_requires_ready_state(self) -> None:
        with patch(
            "src.demo_presentation_writeback.load_json_dict",
            return_value={"overall_state": "presentation_not_ready"},
        ):
            with self.assertRaises(RuntimeError):
                run_presentation_writeback()


if __name__ == "__main__":
    unittest.main()
