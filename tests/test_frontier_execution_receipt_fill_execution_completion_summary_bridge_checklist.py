from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_completion_summary_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierExecutionReceiptFillExecutionCompletionSummaryBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_links_summary_to_handoff(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "combined_fill_execution_status": "fill_execution_ready",
                "awaiting_fill_execution_count": "3",
            }
        )

        self.assertEqual(rows[0]["combined_fill_execution_status"], "fill_execution_ready")
        self.assertEqual(rows[0]["awaiting_fill_execution_count"], "3")
        self.assertIn("fill_execution_handoff", rows[0]["receipt_target"])


if __name__ == "__main__":
    unittest.main()
