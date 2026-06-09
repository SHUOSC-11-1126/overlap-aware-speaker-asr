from __future__ import annotations

import unittest

from src.meeteval_cpwer_execution_status_batch_handoff_completion_summary import (
    build_completion_summary_row,
)


class MeetEvalCpwerExecutionStatusBatchHandoffCompletionSummaryTest(unittest.TestCase):
    def test_build_completion_summary_row_when_all_complete(self) -> None:
        handoff_rows = [
            {"handoff_status": "execution_handoff_complete"},
            {"handoff_status": "execution_handoff_complete"},
        ]

        row = build_completion_summary_row(handoff_rows)

        self.assertEqual(row["queue_status"], "queue_complete")
        self.assertEqual(row["complete_handoff_count"], "2")

    def test_build_completion_summary_row_when_first_ready(self) -> None:
        handoff_rows = [
            {"handoff_status": "execution_handoff_ready"},
            {"handoff_status": "execution_handoff_queued"},
        ]

        row = build_completion_summary_row(handoff_rows)

        self.assertEqual(row["queue_status"], "queue_ready_to_execute")
        self.assertEqual(row["ready_handoff_count"], "1")


if __name__ == "__main__":
    unittest.main()
