from __future__ import annotations

import unittest

from src.demo_go_no_go_board import build_summary_row, classify_go_no_go_state


class DemoGoNoGoBoardTest(unittest.TestCase):
    def test_classify_go_no_go_state_marks_queue_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("queue_complete"), "go")

    def test_classify_go_no_go_state_marks_template_only_as_no_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("template_only"), "no_go")

    def test_classify_go_no_go_state_marks_presentation_writeback_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("presentation_writeback_complete"), "go")

    def test_classify_go_no_go_state_marks_wave5_presentation_extension_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave5_presentation_extension_complete"), "go")

    def test_classify_go_no_go_state_marks_wave6_presentation_extension_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("wave6_presentation_extension_complete"), "go")

    def test_build_summary_row_marks_presentation_writeback_ready(self) -> None:
        rows = [
            {"go_no_go_state": "go"},
            {"go_no_go_state": "go"},
            {"go_no_go_state": "go"},
            {"go_no_go_state": "go"},
            {"go_no_go_state": "no_go"},
            {"go_no_go_state": "no_go"},
        ]

        row = build_summary_row(rows)

        self.assertEqual(row["overall_state"], "presentation_writeback_ready")
        self.assertEqual(row["primary_boundary"], "live_demo_claims_still_blocked")


if __name__ == "__main__":
    unittest.main()
