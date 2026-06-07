from __future__ import annotations

import unittest

from src.meeteval_cpwer_execution_receipt_batch_scaffold_bridge_checklist import build_bridge_checklist_rows


class MeetEvalCpwerExecutionReceiptBatchScaffoldBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_reference_batch_scaffold(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "execution_status": "receipt_batch_scaffold_complete",
                "scaffold_scope": "all_gold_cpwer_execution_receipt",
            },
            [
                {"case_id": "NoOverlap", "preflight_pass": "True"},
                {"case_id": "LightOverlap", "preflight_pass": "True"},
            ],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["preflight_pass_count"], "2")
        self.assertEqual(rows[0]["scaffold_case_count"], "2")
        self.assertIn("meeteval_cpwer_execution_receipt_batch_scaffold.md", rows[0]["prerequisite_artifact"])


if __name__ == "__main__":
    unittest.main()
