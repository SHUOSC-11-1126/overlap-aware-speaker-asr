from __future__ import annotations

import unittest

from src.frontier_operator_next_action_status_handoff_milestone_card import build_milestone_card_row


class FrontierOperatorNextActionStatusHandoffMilestoneCardTest(unittest.TestCase):
    def test_build_milestone_card_row_unlocks_blocked_frontier(self) -> None:
        row = build_milestone_card_row(
            {"total_lane_count": "2"},
            [
                {"frontier_name": "meeteval_compatibility"},
                {"frontier_name": "external_validation"},
            ],
        )

        self.assertEqual(row["next_milestone"], "ready_lane_checkpoint_complete")
        self.assertIn("external_validation", row["unlocks"])
        self.assertEqual(row["remaining_frontier_count"], "1")

    def test_build_milestone_card_row_returns_empty_without_summary(self) -> None:
        row = build_milestone_card_row({}, [])

        self.assertEqual(row, {})


if __name__ == "__main__":
    unittest.main()
