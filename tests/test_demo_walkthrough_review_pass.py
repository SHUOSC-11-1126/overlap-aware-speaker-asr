from __future__ import annotations

import unittest

from src.demo_walkthrough_review_pass import (
    build_review_receipt_rows,
    build_review_row,
    select_first_step,
)


class DemoWalkthroughReviewPassTest(unittest.TestCase):
    def test_select_first_step_uses_queue_head(self) -> None:
        step = select_first_step(
            [{"step_id": "problem_framing", "focus": "problem framing"}]
        )

        self.assertEqual(step["step_id"], "problem_framing")

    def test_build_review_row_marks_complete(self) -> None:
        row = build_review_row({"step_id": "problem_framing", "focus": "problem framing"})

        self.assertEqual(row["review_status"], "review_complete")

    def test_build_review_receipt_rows_document_writeback(self) -> None:
        rows = build_review_receipt_rows({"step_id": "problem_framing"}, 5)

        self.assertEqual(rows[0]["execution_status"], "review_complete")
        self.assertEqual(rows[0]["step_count"], "5")


if __name__ == "__main__":
    unittest.main()
