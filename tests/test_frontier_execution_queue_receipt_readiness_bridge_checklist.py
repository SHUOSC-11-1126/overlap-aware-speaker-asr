from __future__ import annotations

import unittest

from src.frontier_execution_queue_receipt_readiness_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierExecutionQueueReceiptReadinessBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_unified_receipt_queue(self) -> None:
        rows = build_bridge_checklist_rows(
            [
                {
                    "frontier_name": "meeteval_compatibility",
                    "readiness_state": "ready_for_receipt_fill",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["frontier_name"], "meeteval_compatibility")
        self.assertIn("frontier_execution_receipt_queue_status.md", rows[0]["receipt_queue_target"])
        self.assertIn("ready_for_receipt_fill", rows[0]["bridge_note"])

    def test_build_bridge_checklist_rows_preserves_pending_state(self) -> None:
        rows = build_bridge_checklist_rows(
            [
                {
                    "frontier_name": "speaker_profile",
                    "readiness_state": "bridge_or_scaffold_pending",
                }
            ]
        )

        self.assertEqual(rows[0]["readiness_state"], "bridge_or_scaffold_pending")
        self.assertIn("speaker_profile", rows[0]["checklist_goal"])


if __name__ == "__main__":
    unittest.main()
