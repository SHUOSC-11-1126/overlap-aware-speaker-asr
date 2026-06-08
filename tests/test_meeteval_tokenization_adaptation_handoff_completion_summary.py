from __future__ import annotations

import unittest

from src.meeteval_tokenization_adaptation_handoff_completion_summary import build_completion_row


class MeetEvalTokenizationHandoffCompletionSummaryTest(unittest.TestCase):
    def test_build_completion_row_marks_queue_complete(self) -> None:
        row = build_completion_row(
            {
                "handoff_status": "tokenization_adaptation_handoff_ready",
                "aligned_count": "5",
                "total_count": "5",
            }
        )

        self.assertEqual(row["queue_status"], "queue_complete")


if __name__ == "__main__":
    unittest.main()
