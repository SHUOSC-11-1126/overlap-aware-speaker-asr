from __future__ import annotations

import unittest

from src.frontier_operator_next_action_status_handoff_milestone_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierOperatorNextActionStatusHandoffMilestoneBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_links_milestone_to_dashboard(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "next_milestone": "ready_lane_checkpoint_complete",
                "unlocks": "Advance coordination focus to external_validation after the current ready-lane checkpoint closes",
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["next_milestone"], "ready_lane_checkpoint_complete")
        self.assertIn("status_handoff_completion_dashboard.md", rows[0]["receipt_target"])
        self.assertIn("external_validation", rows[0]["bridge_note"])

    def test_build_bridge_checklist_rows_returns_empty_without_milestone(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
