from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_completion_summary import (
    build_completion_summary_row,
)


class FrontierExecutionReceiptFillExecutionCompletionSummaryTest(unittest.TestCase):
    def test_build_completion_summary_row_counts_awaiting_fill(self) -> None:
        row = build_completion_summary_row(
            {
                "meeteval_fill_execution_status": "awaiting_fill",
                "speaker_profile_fill_execution_status": "awaiting_fill",
                "external_staging_fill_execution_status": "awaiting_fill",
                "combined_fill_execution_status": "fill_execution_ready",
            }
        )

        self.assertEqual(row["awaiting_fill_execution_count"], "3")
        self.assertEqual(row["total_frontier_count"], "3")
        self.assertEqual(row["fill_execution_complete_count"], "0")
        self.assertEqual(row["combined_fill_execution_status"], "fill_execution_ready")


if __name__ == "__main__":
    unittest.main()
