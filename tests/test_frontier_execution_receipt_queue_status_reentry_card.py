from __future__ import annotations

import unittest

from src.frontier_execution_receipt_queue_status_reentry_card import build_reentry_card_row


class FrontierExecutionReceiptQueueStatusReentryCardTest(unittest.TestCase):
    def test_build_reentry_card_row_uses_preflight_and_status(self) -> None:
        row = build_reentry_card_row(
            [
                {
                    "current_first_frontier": "meeteval_compatibility",
                    "receipt_target": "results/figures/frontier_execution_receipt_queue_status.md",
                }
            ],
            {"combined_readiness_status": "receipt_ready_to_fill"},
        )

        self.assertEqual(row["current_first_frontier"], "meeteval_compatibility")
        self.assertEqual(row["status_rollup_target"], "results/figures/frontier_execution_receipt_queue_status.md")
        self.assertEqual(row["combined_readiness_status"], "receipt_ready_to_fill")
        self.assertIn("refresh the receipt queue rollup", row["reentry_action"])

    def test_build_reentry_card_row_returns_empty_without_inputs(self) -> None:
        row = build_reentry_card_row([], {})

        self.assertEqual(row, {})


if __name__ == "__main__":
    unittest.main()
