from __future__ import annotations

import unittest

from src.frontier_execution_queue_completion_dashboard import build_dashboard_row


class FrontierExecutionQueueCompletionDashboardBuildRowTest(unittest.TestCase):
    def test_build_dashboard_row_returns_empty_when_inputs_missing(self) -> None:
        self.assertEqual(build_dashboard_row({}, {}), {})
        self.assertEqual(build_dashboard_row({"operator_frontier": "meeteval"}, {}), {})

    def test_build_dashboard_row_composes_operator_and_milestone_fields(self) -> None:
        row = build_dashboard_row(
            {"operator_frontier": "meeteval_compatibility"},
            {"next_milestone": "first_execution_queue_checkpoint_complete", "remaining_frontier_count": "4"},
        )
        self.assertEqual(row["current_first_frontier"], "meeteval_compatibility")
        self.assertEqual(row["next_milestone"], "first_execution_queue_checkpoint_complete")
        self.assertEqual(row["remaining_frontier_count"], "4")
        self.assertEqual(row["dominant_blocker"], "execution_receipt_fill_pending")
        self.assertIn("meeteval_compatibility", row["dashboard_note"])


if __name__ == "__main__":
    unittest.main()
