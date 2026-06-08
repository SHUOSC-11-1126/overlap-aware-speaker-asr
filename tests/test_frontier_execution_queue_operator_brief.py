from __future__ import annotations

import unittest

from src.frontier_execution_queue_operator_brief import build_operator_brief_row


class FrontierExecutionQueueOperatorBriefTest(unittest.TestCase):
    def test_build_operator_brief_row_targets_first_handoff_frontier(self) -> None:
        row = build_operator_brief_row(
            {
                "queue_status": "queue_complete",
                "ready_chain_count": "3",
                "pending_chain_count": "0",
            },
            [
                {
                    "frontier_name": "meeteval_compatibility",
                    "recommended_action": "Fill the execution receipt at results/tables/meeteval_cpwer_execution_receipt.json after final bridge verification.",
                    "expected_outputs": "results/tables/meeteval_cpwer_execution_receipt.json",
                }
            ],
        )

        self.assertEqual(row["operator_frontier"], "meeteval_compatibility")
        self.assertIn("Fill the execution receipt", row["operator_action"])
        self.assertIn("meeteval_cpwer_execution_receipt.json", row["operator_receipt"])
        self.assertIn("queue_complete", row["operator_urgency"])

    def test_build_operator_brief_row_returns_empty_when_no_rows(self) -> None:
        row = build_operator_brief_row({}, [])

        self.assertEqual(row, {})


if __name__ == "__main__":
    unittest.main()
