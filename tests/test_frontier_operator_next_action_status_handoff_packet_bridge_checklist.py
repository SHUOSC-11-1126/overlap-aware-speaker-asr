from __future__ import annotations

import unittest

from src.frontier_operator_next_action_status_handoff_packet_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierOperatorNextActionStatusHandoffPacketBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_uses_reentry_frontier_and_target(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "ready_frontier": "meeteval_compatibility",
                "operator_urgency": "queue_status=queue_complete; ready_lane_count=1; blocked_lane_count=1",
            }
        )

        self.assertEqual(rows[0]["reentry_frontier"], "meeteval_compatibility")
        self.assertIn("queue_status=queue_complete", rows[0]["bridge_note"])
        self.assertIn("status_handoff_operator_brief.md", rows[0]["receipt_target"])

    def test_build_bridge_checklist_rows_defaults_when_missing(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows[0]["reentry_frontier"], "unknown")


if __name__ == "__main__":
    unittest.main()
