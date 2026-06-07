from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_operator_brief import build_operator_brief_row


class FrontierExecutionReceiptFillExecutionOperatorBriefTest(unittest.TestCase):
    def test_build_operator_brief_row_targets_first_handoff_frontier(self) -> None:
        row = build_operator_brief_row(
            {
                "awaiting_fill_execution_count": "3",
                "total_frontier_count": "3",
                "combined_fill_execution_status": "fill_execution_ready",
            },
            [
                {
                    "frontier_name": "meeteval_compatibility",
                    "recommended_action": "Execute the real frontier run.",
                    "expected_outputs": "results/tables/meeteval_cpwer_execution_receipt.json",
                }
            ],
        )

        self.assertEqual(row["operator_frontier"], "meeteval_compatibility")
        self.assertIn("Execute the real frontier run", row["operator_action"])
        self.assertIn("meeteval_cpwer_execution_receipt.json", row["operator_receipt"])


if __name__ == "__main__":
    unittest.main()
