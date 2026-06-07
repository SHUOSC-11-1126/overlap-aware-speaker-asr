from __future__ import annotations

import unittest

from src.meeteval_cpwer_execution_preflight_batch_bridge_checklist import build_bridge_checklist_rows


class MeetEvalCpwerExecutionPreflightBatchBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_execution_receipt(self) -> None:
        rows = build_bridge_checklist_rows(
            {"preflight_pass_count": "5", "preflight_total_count": "5"}
        )

        self.assertIn("meeteval_cpwer_execution_receipt.json", rows[0]["receipt_target"])


if __name__ == "__main__":
    unittest.main()
