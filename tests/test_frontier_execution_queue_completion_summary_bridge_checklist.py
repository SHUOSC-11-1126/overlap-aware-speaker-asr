from __future__ import annotations

import unittest

from src.frontier_execution_queue_completion_summary_bridge_checklist import build_bridge_checklist_rows


class FrontierExecutionQueueCompletionSummaryBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_uses_queue_complete(self) -> None:
        rows = build_bridge_checklist_rows({"queue_status": "queue_complete", "ready_chain_count": "3"})

        self.assertEqual(rows[0]["queue_status"], "queue_complete")
        self.assertIn("ready_chain_count=3", rows[0]["bridge_note"])

    def test_build_bridge_checklist_rows_defaults_queue_status(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows[0]["queue_status"], "queue_in_progress")


if __name__ == "__main__":
    unittest.main()
