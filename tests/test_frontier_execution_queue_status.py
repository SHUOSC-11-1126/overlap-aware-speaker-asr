from __future__ import annotations

import unittest

from src.frontier_execution_queue_status import build_status_row


class FrontierExecutionQueueStatusTest(unittest.TestCase):
    def test_build_status_row_marks_combined_ready_when_all_chains_ready(self) -> None:
        row = build_status_row(
            {"execution_chain_status": "execution_chain_ready"},
            {"execution_chain_status": "execution_chain_ready"},
            {"execution_chain_status": "execution_chain_ready"},
            {"overall_state": "qualitative_writeback_ready"},
            {"overall_state": "presentation_writeback_ready"},
        )

        self.assertEqual(row["combined_chain_status"], "execution_chain_ready")

    def test_build_status_row_marks_combined_in_progress_when_one_chain_pending(self) -> None:
        row = build_status_row(
            {"execution_chain_status": "execution_chain_ready"},
            {"execution_chain_status": "execution_chain_in_progress"},
            {"execution_chain_status": "execution_chain_ready"},
            {"overall_state": "qualitative_writeback_ready"},
            {"overall_state": "presentation_writeback_ready"},
        )

        self.assertEqual(row["combined_chain_status"], "execution_chain_in_progress")

    def test_build_status_row_marks_combined_ready_when_demo_polish_complete(self) -> None:
        row = build_status_row(
            {"execution_chain_status": "execution_chain_ready"},
            {"execution_chain_status": "execution_chain_ready"},
            {"execution_chain_status": "execution_chain_ready"},
            {"overall_state": "qualitative_writeback_ready"},
            {"overall_state": "presentation_polish_complete"},
        )

        self.assertEqual(row["demo_excellence_chain_status"], "execution_chain_ready")
        self.assertEqual(row["combined_chain_status"], "execution_chain_ready")

    def test_build_status_row_marks_combined_in_progress_when_demo_lane_not_ready(self) -> None:
        row = build_status_row(
            {"execution_chain_status": "execution_chain_ready"},
            {"execution_chain_status": "execution_chain_ready"},
            {"execution_chain_status": "execution_chain_ready"},
            {"overall_state": "qualitative_writeback_ready"},
            {"overall_state": "live_demo_claims_blocked"},
        )

        self.assertEqual(row["demo_excellence_chain_status"], "execution_chain_in_progress")
        self.assertEqual(row["combined_chain_status"], "execution_chain_in_progress")


if __name__ == "__main__":
    unittest.main()
