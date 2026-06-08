from __future__ import annotations

import unittest

from src.frontier_operator_next_action_status_handoff_status import build_status_row


class FrontierOperatorNextActionStatusHandoffStatusTest(unittest.TestCase):
    def test_build_status_row_marks_current_chain_as_mixed_ready(self) -> None:
        row = build_status_row(
            {
                "queue_status": "queue_complete",
                "ready_lane_count": "1",
                "blocked_lane_count": "1",
                "primary_frontier": "meeteval_compatibility",
            },
            {
                "next_milestone": "ready_lane_checkpoint_complete",
            },
            {
                "current_first_frontier": "meeteval_compatibility",
            },
            [
                {
                    "receipt_target": "results/figures/frontier_operator_next_action_status_handoff_runbook_card.md",
                }
            ],
        )

        self.assertEqual(row["ready_lane_status"], "ready_lane_active")
        self.assertEqual(row["blocked_lane_status"], "blocked_lane_waiting")
        self.assertEqual(row["milestone_status"], "milestone_active")
        self.assertEqual(row["dashboard_bridge_status"], "dashboard_bridge_ready")
        self.assertEqual(row["combined_status_handoff_state"], "status_handoff_mixed_ready")
        self.assertEqual(row["primary_status_target"], "meeteval_compatibility")

    def test_build_status_row_handles_missing_inputs(self) -> None:
        row = build_status_row({}, {}, {}, [])

        self.assertEqual(row["ready_lane_status"], "ready_lane_empty")
        self.assertEqual(row["blocked_lane_status"], "blocked_lane_clear")
        self.assertEqual(row["milestone_status"], "milestone_missing")
        self.assertEqual(row["dashboard_bridge_status"], "dashboard_bridge_missing")
        self.assertEqual(row["combined_status_handoff_state"], "status_handoff_unset")


if __name__ == "__main__":
    unittest.main()
