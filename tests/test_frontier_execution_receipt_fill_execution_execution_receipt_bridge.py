from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_execution_receipt_bridge import (
    build_execution_receipt_bridge_row,
)


class FrontierExecutionReceiptFillExecutionExecutionReceiptBridgeTest(unittest.TestCase):
    def test_build_execution_receipt_bridge_row_links_evidence_to_json(self) -> None:
        row = build_execution_receipt_bridge_row(
            {"receipt_frontier": "meeteval_compatibility"},
            {"operator_receipt": "results/tables/meeteval_cpwer_execution_receipt.json"},
        )

        self.assertIn("meeteval_cpwer_execution_receipt.json", row["execution_receipt_target"])


if __name__ == "__main__":
    unittest.main()
