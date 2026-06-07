from __future__ import annotations

import unittest

from src.meeteval_cpwer_execution_receipt_readiness import build_readiness_row


class MeetEvalCpwerExecutionReceiptReadinessTest(unittest.TestCase):
    def test_build_readiness_row_marks_ready_when_chain_and_template_pass(self) -> None:
        row = build_readiness_row(
            {"case_id": "NoOverlap", "execution_chain_status": "execution_chain_ready"},
            {"case_id": "NoOverlap", "execution_status": "template_only", "preflight_pass": "True"},
        )

        self.assertEqual(row["readiness_status"], "receipt_ready_to_fill")

    def test_build_readiness_row_marks_not_ready_when_chain_pending(self) -> None:
        row = build_readiness_row(
            {"execution_chain_status": "execution_chain_in_progress"},
            {"execution_status": "template_only", "preflight_pass": "True"},
        )

        self.assertEqual(row["readiness_status"], "receipt_not_ready")


if __name__ == "__main__":
    unittest.main()
