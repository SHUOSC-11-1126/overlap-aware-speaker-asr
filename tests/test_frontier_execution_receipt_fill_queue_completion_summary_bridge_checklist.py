from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_queue_completion_summary_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierExecutionReceiptFillQueueCompletionSummaryBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_uses_fill_queue_ready(self) -> None:
        rows = build_bridge_checklist_rows(
            {"combined_fill_status": "fill_queue_ready", "awaiting_fill_count": "3"}
        )

        self.assertEqual(rows[0]["combined_fill_status"], "fill_queue_ready")
        self.assertIn("fill_queue_handoff", rows[0]["receipt_target"])


if __name__ == "__main__":
    unittest.main()
