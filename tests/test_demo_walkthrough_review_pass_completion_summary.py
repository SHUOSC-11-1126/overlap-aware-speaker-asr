from __future__ import annotations

import unittest

from src.demo_walkthrough_review_pass_completion_summary import build_completion_summary_row


class DemoWalkthroughReviewPassCompletionSummaryTest(unittest.TestCase):
    def test_build_completion_summary_row_marks_queue_complete(self) -> None:
        row = build_completion_summary_row(
            {
                "queue_status": "queue_complete",
                "completed_count": "5",
                "total_step_count": "5",
                "pending_count": "0",
            }
        )

        self.assertEqual(row["queue_status"], "queue_complete")
        self.assertEqual(row["scope"], "walkthrough_review_queue")

    def test_build_completion_summary_row_marks_in_progress(self) -> None:
        row = build_completion_summary_row(
            {
                "queue_status": "queue_in_progress",
                "completed_count": "3",
                "total_step_count": "5",
                "pending_count": "2",
            }
        )

        self.assertEqual(row["queue_status"], "queue_in_progress")


if __name__ == "__main__":
    unittest.main()
