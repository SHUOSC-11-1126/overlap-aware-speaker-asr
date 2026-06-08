from __future__ import annotations

import unittest

from src.frontier_execution_receipt_queue_runbook_bridge_checklist import build_bridge_checklist_rows


class FrontierExecutionReceiptQueueRunbookBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_receipt(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "recommended_frontier": "meeteval_compatibility",
                "runbook_note": "Start with meeteval_compatibility.",
                "completion_signal": (
                    "receipt queue verification is complete and the target receipt "
                    "results/tables/meeteval_cpwer_execution_receipt.json is ready to update"
                ),
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["recommended_frontier"], "meeteval_compatibility")
        self.assertIn("meeteval_cpwer_execution_receipt.json", rows[0]["receipt_target"])
        self.assertIn("Start with meeteval_compatibility", rows[0]["bridge_note"])

    def test_build_bridge_checklist_rows_returns_empty_without_runbook(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
