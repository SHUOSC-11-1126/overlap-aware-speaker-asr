from __future__ import annotations

import unittest

from src.frontier_execution_receipt_queue_milestone_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierExecutionReceiptQueueMilestoneBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_links_milestone_to_dashboard(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "next_milestone": "first_receipt_queue_checkpoint_complete",
                "unlocks": "Advance coordination focus to speaker_profile after the current first checkpoint closes",
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["next_milestone"], "first_receipt_queue_checkpoint_complete")
        self.assertIn("frontier_execution_receipt_queue_completion_dashboard.md", rows[0]["receipt_target"])
        self.assertIn("speaker_profile", rows[0]["bridge_note"])

    def test_build_bridge_checklist_rows_returns_empty_without_milestone(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
