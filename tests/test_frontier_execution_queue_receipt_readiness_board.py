from __future__ import annotations

import unittest

from src.frontier_execution_queue_receipt_readiness_board import build_readiness_rows


class FrontierExecutionQueueReceiptReadinessBoardTest(unittest.TestCase):
    def test_build_readiness_rows_marks_ready_receipts(self) -> None:
        rows = build_readiness_rows(
            [
                {
                    "frontier_name": "meeteval_compatibility",
                    "chain_status": "execution_chain_ready",
                    "expected_outputs": "results/tables/meeteval_cpwer_execution_receipt.json",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["readiness_state"], "ready_for_receipt_fill")
        self.assertIn("frontier_execution_queue_handoff_bridge_checklist.md", rows[0]["next_verification_artifact"])

    def test_build_readiness_rows_marks_pending_receipts(self) -> None:
        rows = build_readiness_rows(
            [
                {
                    "frontier_name": "external_validation",
                    "chain_status": "execution_chain_in_progress",
                    "expected_outputs": "results/tables/external_validation_slice_staging_handoff_receipt.json",
                }
            ]
        )

        self.assertEqual(rows[0]["readiness_state"], "bridge_or_scaffold_pending")
        self.assertIn("execution_chain_in_progress", rows[0]["readiness_note"])


if __name__ == "__main__":
    unittest.main()
