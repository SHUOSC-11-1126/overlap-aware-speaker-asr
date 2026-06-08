from __future__ import annotations

import unittest

from src.frontier_execution_queue_status_reentry_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierExecutionQueueStatusReentryBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_links_reentry_to_handoff_bridge(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "current_first_frontier": "meeteval_compatibility",
                "reentry_action": (
                    "After status preflight is confirmed, reopen "
                    "results/figures/frontier_execution_queue_status.md and refresh the execution queue rollup."
                ),
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["current_first_frontier"], "meeteval_compatibility")
        self.assertIn("frontier_execution_queue_handoff_bridge_checklist.md", rows[0]["receipt_target"])
        self.assertIn("refresh the execution queue rollup", rows[0]["bridge_note"])

    def test_build_bridge_checklist_rows_returns_empty_without_reentry_card(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
