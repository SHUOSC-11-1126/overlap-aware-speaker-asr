from __future__ import annotations

import unittest

from src.frontier_execution_receipt_queue_receipt_open_card import build_receipt_open_card_row


class FrontierExecutionReceiptQueueReceiptOpenCardTest(unittest.TestCase):
    def test_build_receipt_open_card_row_targets_first_receipt(self) -> None:
        row = build_receipt_open_card_row(
            [
                {
                    "frontier_name": "meeteval_compatibility",
                    "readiness_status": "receipt_ready_to_fill",
                    "receipt_target": "results/tables/meeteval_cpwer_execution_receipt.json",
                }
            ]
        )

        self.assertEqual(row["frontier_name"], "meeteval_compatibility")
        self.assertEqual(row["readiness_status"], "receipt_ready_to_fill")
        self.assertIn("meeteval_cpwer_execution_receipt.json", row["receipt_target"])
        self.assertIn("Open", row["open_action"])

    def test_build_receipt_open_card_row_returns_empty_without_bridge_rows(self) -> None:
        row = build_receipt_open_card_row([])

        self.assertEqual(row, {})


if __name__ == "__main__":
    unittest.main()
