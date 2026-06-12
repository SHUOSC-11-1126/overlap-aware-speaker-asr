from __future__ import annotations

import unittest

from src.llm_critic_go_no_go_board import build_checkpoint_rows, build_summary_row, classify_go_no_go_state


class LlmCriticGoNoGoBoardTest(unittest.TestCase):
    def test_classify_go_no_go_state_marks_queue_complete_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("queue_complete"), "go")

    def test_classify_go_no_go_state_marks_template_only_as_no_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("template_only"), "no_go")

    def test_build_checkpoint_rows_marks_status_rollup_complete_when_all_passes_done(self) -> None:
        rows = build_checkpoint_rows()
        rollup = next(row for row in rows if row["checkpoint_name"] == "review_status_rollup")
        self.assertEqual(rollup["current_status"], "queue_complete")
        self.assertEqual(rollup["go_no_go_state"], "go")

    def test_build_summary_row_marks_qualitative_writeback_ready(self) -> None:
        rows = [
            {"go_no_go_state": "go"},
            {"go_no_go_state": "go"},
            {"go_no_go_state": "go"},
            {"go_no_go_state": "go"},
            {"go_no_go_state": "no_go"},
        ]

        row = build_summary_row(rows)

        self.assertEqual(row["overall_state"], "qualitative_writeback_ready")
        self.assertEqual(row["primary_boundary"], "verified_repair_claims_still_blocked")


if __name__ == "__main__":
    unittest.main()
