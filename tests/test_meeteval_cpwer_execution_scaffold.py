from __future__ import annotations

import unittest

from src.meeteval_cpwer_execution_scaffold import build_scaffold_receipt_rows, build_scaffold_row


class MeetEvalCpwerExecutionScaffoldTest(unittest.TestCase):
    def test_build_scaffold_row_records_scaffold_only(self) -> None:
        row = build_scaffold_row(
            {
                "case_id": "NoOverlap",
                "bridge_status": "cpwer_bridge_complete",
                "cpwer_bridge_lite": "0.12",
            }
        )

        self.assertEqual(row["case_id"], "NoOverlap")
        self.assertEqual(row["scaffold_status"], "scaffold_only")

    def test_build_scaffold_receipt_rows_document_scaffold(self) -> None:
        rows = build_scaffold_receipt_rows({"case_id": "NoOverlap"})

        self.assertEqual(rows[0]["execution_status"], "scaffold_complete")


if __name__ == "__main__":
    unittest.main()
