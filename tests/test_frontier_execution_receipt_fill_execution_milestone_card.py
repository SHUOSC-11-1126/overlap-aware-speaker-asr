from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_milestone_card import build_milestone_card_row


class FrontierExecutionReceiptFillExecutionMilestoneCardTest(unittest.TestCase):
    def test_build_milestone_card_row_unlocks_second_frontier(self) -> None:
        row = build_milestone_card_row(
            {"awaiting_fill_execution_count": "3", "total_frontier_count": "3"},
            [
                {"frontier_name": "meeteval_compatibility"},
                {"frontier_name": "speaker_profile"},
            ],
        )

        self.assertEqual(row["next_milestone"], "first_execution_receipt_filled")
        self.assertIn("speaker_profile", row["unlocks"])


if __name__ == "__main__":
    unittest.main()
