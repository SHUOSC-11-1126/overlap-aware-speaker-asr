from __future__ import annotations

import unittest

from src.frontier_operator_next_action_handoff_packet_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierOperatorNextActionHandoffPacketBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_points_back_to_operator_card(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "coordination_state": "mixed_ready_state",
                "operator_sequence": "ready_lane:meeteval_compatibility -> blocked_lane:external_validation",
            }
        )

        self.assertEqual(rows[0]["coordination_state"], "mixed_ready_state")
        self.assertIn("frontier_operator_next_action_card.md", rows[0]["receipt_target"])
        self.assertIn("ready_lane:meeteval_compatibility", rows[0]["bridge_note"])


if __name__ == "__main__":
    unittest.main()
