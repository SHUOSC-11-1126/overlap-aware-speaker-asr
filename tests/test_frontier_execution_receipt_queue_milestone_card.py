from __future__ import annotations

import unittest

from src.frontier_execution_receipt_queue_milestone_card import build_milestone_card_row


class FrontierExecutionReceiptQueueMilestoneCardTest(unittest.TestCase):
    def test_build_milestone_card_row_unlocks_second_frontier(self) -> None:
        row = build_milestone_card_row(
            {"ready_receipt_count": "3", "total_receipt_count": "3"},
            [
                {"frontier_name": "meeteval_compatibility"},
                {"frontier_name": "speaker_profile"},
            ],
        )

        self.assertEqual(row["next_milestone"], "first_receipt_queue_checkpoint_complete")
        self.assertIn("speaker_profile", row["unlocks"])
        self.assertEqual(row["remaining_frontier_count"], "2")

    def test_build_milestone_card_row_returns_empty_without_summary(self) -> None:
        row = build_milestone_card_row({}, [])

        self.assertEqual(row, {})


if __name__ == "__main__":
    unittest.main()
