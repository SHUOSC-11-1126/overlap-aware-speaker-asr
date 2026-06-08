from __future__ import annotations

import unittest

from src.frontier_execution_receipt_queue_status_preflight_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierExecutionReceiptQueueStatusPreflightBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_status_rollup(self) -> None:
        rows = build_bridge_checklist_rows(
            [
                {
                    "current_first_frontier": "meeteval_compatibility",
                    "next_gate": "Confirm this bridge before opening the receipt queue runbook card target.",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["current_first_frontier"], "meeteval_compatibility")
        self.assertIn("frontier_execution_receipt_queue_status.md", rows[0]["receipt_target"])
        self.assertIn("receipt queue runbook card target", rows[0]["bridge_note"])

    def test_build_bridge_checklist_rows_returns_empty_without_dashboard_bridge(self) -> None:
        rows = build_bridge_checklist_rows([])

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
