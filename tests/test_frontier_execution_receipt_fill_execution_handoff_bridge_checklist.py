from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_handoff_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierExecutionReceiptFillExecutionHandoffBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_maps_handoff_to_receipt(self) -> None:
        rows = build_bridge_checklist_rows(
            [
                {
                    "handoff_order": "1",
                    "frontier_name": "meeteval_compatibility",
                    "fill_execution_status": "awaiting_fill",
                    "expected_outputs": "results/tables/meeteval_cpwer_execution_receipt.json",
                }
            ]
        )

        self.assertEqual(rows[0]["frontier_name"], "meeteval_compatibility")
        self.assertEqual(
            rows[0]["receipt_target"],
            "results/tables/meeteval_cpwer_execution_receipt.json",
        )
        self.assertIn("meeteval_compatibility", rows[0]["next_gate"])


if __name__ == "__main__":
    unittest.main()
