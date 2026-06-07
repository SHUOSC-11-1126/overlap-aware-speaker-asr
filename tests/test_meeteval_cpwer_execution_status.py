from __future__ import annotations

import unittest

from src.meeteval_cpwer_execution_status import build_status_row


class MeetEvalCpwerExecutionStatusTest(unittest.TestCase):
    def test_build_status_row_marks_chain_ready_when_preflight_and_scaffold_pass(self) -> None:
        row = build_status_row(
            {"case_id": "NoOverlap", "preflight_pass": True},
            {"case_id": "NoOverlap", "scaffold_status": "receipt_scaffold_only"},
            "template_only",
        )

        self.assertEqual(row["execution_chain_status"], "execution_chain_ready")

    def test_build_status_row_marks_chain_in_progress_when_preflight_fails(self) -> None:
        row = build_status_row(
            {"case_id": "NoOverlap", "preflight_pass": False},
            {"scaffold_status": "receipt_scaffold_only"},
            "template_only",
        )

        self.assertEqual(row["execution_chain_status"], "execution_chain_in_progress")


if __name__ == "__main__":
    unittest.main()
