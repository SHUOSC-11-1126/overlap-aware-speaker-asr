from __future__ import annotations

import unittest

from src.meeteval_cpwer_execution_handoff import build_handoff_receipt_rows, build_handoff_row


class MeetEvalCpwerExecutionHandoffTest(unittest.TestCase):
    def test_build_handoff_row_targets_execution_receipt(self) -> None:
        row = build_handoff_row(
            {
                "case_id": "NoOverlap",
                "scaffold_status": "scaffold_only",
                "cpwer_bridge_lite": "0.12",
            }
        )

        self.assertEqual(row["case_id"], "NoOverlap")
        self.assertIn("execution_receipt", row["expected_evidence"])

    def test_build_handoff_receipt_rows_document_handoff(self) -> None:
        rows = build_handoff_receipt_rows({"case_id": "NoOverlap"})

        self.assertEqual(rows[0]["execution_status"], "handoff_documented")


if __name__ == "__main__":
    unittest.main()
