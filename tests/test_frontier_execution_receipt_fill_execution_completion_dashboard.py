from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_completion_dashboard import build_dashboard_row


class FrontierExecutionReceiptFillExecutionCompletionDashboardTest(unittest.TestCase):
    def test_build_dashboard_row_summarizes_queue_state(self) -> None:
        row = build_dashboard_row(
            {"operator_frontier": "meeteval_compatibility"},
            {
                "awaiting_fill_execution_count": "3",
                "total_frontier_count": "3",
                "combined_fill_execution_status": "fill_execution_ready",
            },
        )

        self.assertEqual(row["current_first_frontier"], "meeteval_compatibility")
        self.assertEqual(row["combined_fill_execution_status"], "fill_execution_ready")


if __name__ == "__main__":
    unittest.main()
