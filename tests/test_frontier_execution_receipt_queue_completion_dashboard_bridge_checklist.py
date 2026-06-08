from __future__ import annotations

import unittest

from src.frontier_execution_receipt_queue_completion_dashboard_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierExecutionReceiptQueueCompletionDashboardBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_runbook(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "current_first_frontier": "meeteval_compatibility",
                "dashboard_note": "meeteval_compatibility leads the receipt queue.",
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["current_first_frontier"], "meeteval_compatibility")
        self.assertIn("frontier_execution_receipt_queue_runbook_card.md", rows[0]["receipt_target"])
        self.assertIn("meeteval_compatibility leads the receipt queue", rows[0]["bridge_note"])

    def test_build_bridge_checklist_rows_returns_empty_without_dashboard(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
