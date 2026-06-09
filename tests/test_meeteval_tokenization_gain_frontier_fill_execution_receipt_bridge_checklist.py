from __future__ import annotations

import unittest

from src.meeteval_tokenization_gain_frontier_fill_execution_receipt_bridge_checklist import (
    build_bridge_checklist_rows,
)


class MeetEvalTokenizationGainFrontierFillExecutionReceiptBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_links_receipt_bridge_to_receipt(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "recommended_frontier": "meeteval_compatibility",
                "prerequisite_artifact": (
                    "results/figures/meeteval_tokenization_gain_frontier_fill_runbook_bridge_checklist.md"
                ),
                "execution_receipt_target": "results/tables/meeteval_cpwer_execution_receipt.json",
                "bridge_note": "No full MeetEval benchmark completion is claimed by this bridge alone.",
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["recommended_frontier"], "meeteval_compatibility")
        self.assertIn("execution_receipt_bridge", rows[0]["prerequisite_artifact"])
        self.assertEqual(rows[0]["receipt_target"], "results/tables/meeteval_cpwer_execution_receipt.json")
        self.assertIn("is claimed until real evidence", rows[0]["next_gate"])

    def test_build_bridge_checklist_rows_empty_when_bridge_missing(self) -> None:
        self.assertEqual(build_bridge_checklist_rows({}), [])


if __name__ == "__main__":
    unittest.main()
