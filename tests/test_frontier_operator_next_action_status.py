from __future__ import annotations

import unittest

from src.frontier_operator_next_action_status import build_status_row


class FrontierOperatorNextActionStatusTest(unittest.TestCase):
    def test_build_status_row_marks_current_chain_as_mixed_ready(self) -> None:
        row = build_status_row(
            {
                "coordination_state": "mixed_ready_state",
                "ready_frontier": "meeteval_compatibility",
                "blocked_frontier": "external_validation",
            },
            {
                "next_milestone": "ready_lane_checkpoint_complete",
            },
            {
                "current_first_frontier": "meeteval_compatibility",
            },
            [
                {
                    "receipt_target": "results/figures/frontier_operator_next_action_runbook_card.md",
                }
            ],
        )

        self.assertEqual(row["ready_lane_status"], "ready_lane_active")
        self.assertEqual(row["blocked_lane_status"], "blocked_lane_waiting")
        self.assertEqual(row["milestone_status"], "milestone_active")
        self.assertEqual(row["dashboard_bridge_status"], "dashboard_bridge_ready")
        self.assertEqual(row["combined_operator_status"], "operator_status_mixed_ready")
        self.assertEqual(row["primary_status_target"], "meeteval_compatibility")

    def test_build_status_row_handles_missing_inputs(self) -> None:
        row = build_status_row({}, {}, {}, [])

        self.assertEqual(row["ready_lane_status"], "ready_lane_empty")
        self.assertEqual(row["blocked_lane_status"], "blocked_lane_clear")
        self.assertEqual(row["milestone_status"], "milestone_missing")
        self.assertEqual(row["dashboard_bridge_status"], "dashboard_bridge_missing")
        self.assertEqual(row["combined_operator_status"], "operator_status_unset")


if __name__ == "__main__":
    unittest.main()
