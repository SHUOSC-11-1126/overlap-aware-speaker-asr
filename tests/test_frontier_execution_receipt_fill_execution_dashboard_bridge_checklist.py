from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_dashboard_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierExecutionReceiptFillExecutionDashboardBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_links_dashboard_to_runbook(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "current_first_frontier": "meeteval_compatibility",
                "dashboard_note": "Queue snapshot.",
            }
        )

        self.assertIn("runbook_card", rows[0]["receipt_target"])


if __name__ == "__main__":
    unittest.main()
