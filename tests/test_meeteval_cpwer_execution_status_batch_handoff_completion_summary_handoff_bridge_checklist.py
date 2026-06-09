from __future__ import annotations

import unittest

from src.meeteval_cpwer_execution_status_batch_handoff_completion_summary_handoff_bridge_checklist import (
    build_bridge_checklist_rows,
)


class MeetEvalCpwerExecutionStatusBatchHandoffCompletionSummaryHandoffBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_when_handoff_ready(self) -> None:
        handoff_rows = [
            {
                "handoff_status": "batch_handoff_completion_handoff_ready",
                "queue_status": "queue_complete",
                "complete_handoff_count": "5",
                "total_handoff_count": "5",
            }
        ]

        rows = build_bridge_checklist_rows(handoff_rows)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["handoff_status"], "batch_handoff_completion_handoff_ready")

    def test_build_bridge_checklist_rows_empty_when_handoff_missing(self) -> None:
        self.assertEqual(build_bridge_checklist_rows([]), [])


if __name__ == "__main__":
    unittest.main()
