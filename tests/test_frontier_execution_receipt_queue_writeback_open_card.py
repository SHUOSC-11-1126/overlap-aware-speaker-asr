from __future__ import annotations

import unittest

from src.frontier_execution_receipt_queue_writeback_open_card import (
    build_writeback_open_card_row,
)


class FrontierExecutionReceiptQueueWritebackOpenCardTest(unittest.TestCase):
    def test_build_writeback_open_card_row_targets_first_pending_receipt(self) -> None:
        row = build_writeback_open_card_row(
            [
                {
                    "frontier_name": "meeteval_compatibility",
                    "writeback_status": "writeback_complete",
                    "receipt_target": "results/tables/meeteval_cpwer_execution_receipt.json",
                },
                {
                    "frontier_name": "speaker_profile",
                    "writeback_status": "awaiting_writeback",
                    "receipt_target": "results/tables/speaker_profile_embedding_trial_execution_receipt.json",
                },
            ]
        )

        self.assertEqual(row["frontier_name"], "speaker_profile")
        self.assertEqual(row["writeback_status"], "awaiting_writeback")
        self.assertIn("speaker_profile_embedding_trial_execution_receipt.json", row["receipt_target"])

    def test_build_writeback_open_card_row_returns_empty_without_bridge_rows(self) -> None:
        row = build_writeback_open_card_row([])

        self.assertEqual(row, {})


if __name__ == "__main__":
    unittest.main()
