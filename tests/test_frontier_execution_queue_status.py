from __future__ import annotations

import unittest

from src.frontier_execution_queue_status import build_status_row


class FrontierExecutionQueueStatusTest(unittest.TestCase):
    def test_build_status_row_marks_combined_ready_when_all_chains_ready(self) -> None:
        row = build_status_row(
            {"execution_chain_status": "execution_chain_ready"},
            {"execution_chain_status": "execution_chain_ready"},
            {"execution_chain_status": "execution_chain_ready"},
        )

        self.assertEqual(row["combined_chain_status"], "execution_chain_ready")

    def test_build_status_row_marks_combined_in_progress_when_one_chain_pending(self) -> None:
        row = build_status_row(
            {"execution_chain_status": "execution_chain_ready"},
            {"execution_chain_status": "execution_chain_in_progress"},
            {"execution_chain_status": "execution_chain_ready"},
        )

        self.assertEqual(row["combined_chain_status"], "execution_chain_in_progress")


if __name__ == "__main__":
    unittest.main()
