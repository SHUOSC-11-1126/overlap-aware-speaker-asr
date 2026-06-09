from __future__ import annotations

import unittest

from src.meeteval_tokenization_gain_frontier_fill_execution_receipt_bridge import (
    build_execution_receipt_bridge_row,
)


class MeetEvalTokenizationGainFrontierFillExecutionReceiptBridgeTest(unittest.TestCase):
    def test_build_execution_receipt_bridge_row_links_runbook_bridge_to_receipt(self) -> None:
        row = build_execution_receipt_bridge_row(
            {
                "runbook_status": "tokenization_gain_frontier_fill_runbook_ready",
                "recommended_frontier": "meeteval_compatibility",
                "execution_receipt_target": "results/tables/meeteval_cpwer_execution_receipt.json",
                "bridge_note": "Runbook status=tokenization_gain_frontier_fill_runbook_ready; adapted_case_ratio=5/5.",
            }
        )

        self.assertEqual(row["recommended_frontier"], "meeteval_compatibility")
        self.assertIn("meeteval_tokenization_gain_frontier_fill_runbook_bridge_checklist", row["prerequisite_artifact"])
        self.assertEqual(row["execution_receipt_target"], "results/tables/meeteval_cpwer_execution_receipt.json")
        self.assertIn("not claimed by this bridge alone", row["bridge_note"])

    def test_build_execution_receipt_bridge_row_empty_when_bridge_missing(self) -> None:
        self.assertEqual(build_execution_receipt_bridge_row({}), {})


if __name__ == "__main__":
    unittest.main()
