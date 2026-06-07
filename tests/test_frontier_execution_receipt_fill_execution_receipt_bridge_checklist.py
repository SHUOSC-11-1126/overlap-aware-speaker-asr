from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_receipt_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierExecutionReceiptFillExecutionReceiptBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_receipt_gate(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "operator_frontier": "meeteval_compatibility",
                "prerequisite_artifact": "results/figures/frontier_execution_receipt_fill_execution_operator_brief.md",
                "receipt_target": "results/tables/meeteval_cpwer_execution_receipt.json",
                "bridge_note": "Open the operator brief first.",
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertIn("meeteval_cpwer_execution_receipt.json", rows[0]["next_gate"])


if __name__ == "__main__":
    unittest.main()
