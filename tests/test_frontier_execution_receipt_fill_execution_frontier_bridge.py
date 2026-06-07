from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_frontier_bridge import build_frontier_bridge_row


class FrontierExecutionReceiptFillExecutionFrontierBridgeTest(unittest.TestCase):
    def test_build_frontier_bridge_row_aligns_queue_head(self) -> None:
        row = build_frontier_bridge_row(
            {"recommended_frontier": "meeteval_compatibility"},
            "meeteval_compatibility",
        )

        self.assertEqual(row["fill_execution_frontier"], "meeteval_compatibility")
        self.assertEqual(row["frontier_queue_head"], "meeteval_compatibility")


if __name__ == "__main__":
    unittest.main()
