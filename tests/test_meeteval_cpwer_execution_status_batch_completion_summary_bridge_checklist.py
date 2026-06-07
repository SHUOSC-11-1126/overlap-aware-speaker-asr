from __future__ import annotations

import unittest

from src.meeteval_cpwer_execution_status_batch_completion_summary_bridge_checklist import (
    build_bridge_checklist_rows,
)


class MeetEvalCpwerExecutionStatusBatchCompletionSummaryBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_from_summary(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "queue_status": "queue_complete",
                "ready_chain_count": "5",
                "total_chain_count": "5",
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["queue_status"], "queue_complete")
        self.assertIn("batch_handoff", rows[0]["receipt_target"])


if __name__ == "__main__":
    unittest.main()
