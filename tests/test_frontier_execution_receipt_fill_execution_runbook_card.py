from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_runbook_card import build_runbook_card_row


class FrontierExecutionReceiptFillExecutionRunbookCardTest(unittest.TestCase):
    def test_build_runbook_card_row_targets_first_frontier(self) -> None:
        row = build_runbook_card_row(
            {
                "operator_frontier": "meeteval_compatibility",
                "operator_action": "Execute the real frontier run.",
                "operator_evidence": "handoff artifacts",
            },
            {
                "receipt_completion_signal": "execution_status is no longer template_only",
                "receipt_evidence": "evidence artifacts",
            },
            {"awaiting_fill_execution_count": "3", "total_frontier_count": "3"},
        )

        self.assertEqual(row["recommended_frontier"], "meeteval_compatibility")
        self.assertIn("3/3", row["urgency"])


if __name__ == "__main__":
    unittest.main()
