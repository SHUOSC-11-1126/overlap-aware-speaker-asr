from __future__ import annotations

import unittest

from src.frontier_execution_queue_completion_summary import build_completion_summary_row


class FrontierExecutionQueueCompletionSummaryTest(unittest.TestCase):
    def test_build_completion_summary_row_marks_queue_complete_when_all_ready(self) -> None:
        row = build_completion_summary_row(
            {
                "meeteval_chain_status": "execution_chain_ready",
                "speaker_profile_chain_status": "execution_chain_ready",
                "external_staging_chain_status": "execution_chain_ready",
            }
        )

        self.assertEqual(row["queue_status"], "queue_complete")
        self.assertEqual(row["ready_chain_count"], "3")
        self.assertEqual(row["pending_chain_count"], "0")

    def test_build_completion_summary_row_marks_queue_in_progress_when_one_pending(self) -> None:
        row = build_completion_summary_row(
            {
                "meeteval_chain_status": "execution_chain_ready",
                "speaker_profile_chain_status": "execution_chain_in_progress",
                "external_staging_chain_status": "execution_chain_ready",
            }
        )

        self.assertEqual(row["queue_status"], "queue_in_progress")
        self.assertEqual(row["pending_chain_count"], "1")


if __name__ == "__main__":
    unittest.main()
