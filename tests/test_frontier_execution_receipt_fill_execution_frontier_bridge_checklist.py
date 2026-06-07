from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_frontier_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierExecutionReceiptFillExecutionFrontierBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_runbook(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "fill_execution_frontier": "meeteval_compatibility",
                "frontier_queue_head": "meeteval_compatibility",
                "bridge_note": "Aligned queue heads.",
            }
        )

        self.assertIn("runbook_card", rows[0]["receipt_target"])


if __name__ == "__main__":
    unittest.main()
