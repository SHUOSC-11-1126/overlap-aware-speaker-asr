from __future__ import annotations

import unittest

from src.meeteval_cpwer_execution_receipt_readiness_bridge_checklist import build_bridge_checklist_rows


class MeetEvalCpwerExecutionReceiptReadinessBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_uses_readiness_status(self) -> None:
        rows = build_bridge_checklist_rows(
            {"case_id": "NoOverlap", "readiness_status": "receipt_ready_to_fill", "preflight_pass": "True"}
        )

        self.assertEqual(rows[0]["readiness_status"], "receipt_ready_to_fill")

    def test_build_bridge_checklist_rows_defaults_case_id(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows[0]["case_id"], "NoOverlap")


if __name__ == "__main__":
    unittest.main()
