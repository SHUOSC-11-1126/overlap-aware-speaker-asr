from __future__ import annotations

import unittest

from src.frontier_operator_next_action_status_handoff_completion_summary import build_completion_summary_row


class FrontierOperatorNextActionStatusHandoffCompletionSummaryTest(unittest.TestCase):
    def test_build_completion_summary_row_marks_queue_complete_for_mixed_state(self) -> None:
        row = build_completion_summary_row(
            [
                {
                    "action_lane": "ready_lane",
                    "frontier_name": "meeteval_compatibility",
                },
                {
                    "action_lane": "blocked_lane",
                    "frontier_name": "external_validation",
                },
            ]
        )

        self.assertEqual(row["ready_lane_count"], "1")
        self.assertEqual(row["blocked_lane_count"], "1")
        self.assertEqual(row["queue_status"], "queue_complete")
        self.assertEqual(row["primary_frontier"], "meeteval_compatibility")

    def test_build_completion_summary_row_handles_empty_state(self) -> None:
        row = build_completion_summary_row([])

        self.assertEqual(row["total_lane_count"], "0")
        self.assertEqual(row["queue_status"], "queue_empty")


if __name__ == "__main__":
    unittest.main()
