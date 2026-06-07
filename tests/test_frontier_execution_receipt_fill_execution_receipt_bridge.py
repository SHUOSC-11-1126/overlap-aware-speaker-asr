from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_receipt_bridge import build_receipt_bridge_row


class FrontierExecutionReceiptFillExecutionReceiptBridgeTest(unittest.TestCase):
    def test_build_receipt_bridge_row_links_operator_brief_to_receipt(self) -> None:
        row = build_receipt_bridge_row(
            {
                "operator_frontier": "meeteval_compatibility",
                "operator_receipt": "results/tables/meeteval_cpwer_execution_receipt.json",
            }
        )

        self.assertEqual(row["operator_frontier"], "meeteval_compatibility")
        self.assertIn("operator_brief", row["prerequisite_artifact"])
        self.assertIn("meeteval_cpwer_execution_receipt.json", row["receipt_target"])


if __name__ == "__main__":
    unittest.main()
