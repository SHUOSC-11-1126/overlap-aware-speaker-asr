from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_evidence_receipt import build_evidence_receipt_row


class FrontierExecutionReceiptFillExecutionEvidenceReceiptTest(unittest.TestCase):
    def test_build_evidence_receipt_row_targets_operator_frontier(self) -> None:
        row = build_evidence_receipt_row(
            {
                "operator_frontier": "meeteval_compatibility",
                "operator_action": "Execute the real frontier run.",
                "operator_receipt": "results/tables/meeteval_cpwer_execution_receipt.json",
                "operator_evidence": "handoff and bridge checklist",
            }
        )

        self.assertEqual(row["receipt_frontier"], "meeteval_compatibility")
        self.assertIn("template_only", row["receipt_completion_signal"])


if __name__ == "__main__":
    unittest.main()
