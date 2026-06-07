from __future__ import annotations

import unittest

from src.meeteval_cpwer_execution_receipt_batch_scaffold import (
    build_scaffold_receipt_rows,
    build_scaffold_row,
    build_scaffold_rows,
)


class MeetEvalCpwerExecutionReceiptBatchScaffoldTest(unittest.TestCase):
    def test_build_scaffold_row_records_batch_scaffold_only(self) -> None:
        row = build_scaffold_row(
            {
                "case_id": "NoOverlap",
                "preflight_pass": True,
                "hypothesis_source": "separated_whisper",
            }
        )

        self.assertEqual(row["scaffold_status"], "receipt_batch_scaffold_only")
        self.assertEqual(row["preflight_pass"], "True")

    def test_build_scaffold_rows_cover_all_gold_cases(self) -> None:
        rows = build_scaffold_rows([])

        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["case_id"], "NoOverlap")

    def test_build_scaffold_receipt_rows_document_batch_scaffold(self) -> None:
        rows = build_scaffold_receipt_rows(
            [
                {"case_id": "NoOverlap", "preflight_pass": "True"},
                {"case_id": "LightOverlap", "preflight_pass": "True"},
            ]
        )

        self.assertEqual(rows[0]["execution_status"], "receipt_batch_scaffold_complete")
        self.assertEqual(rows[0]["scaffold_scope"], "all_gold_cpwer_execution_receipt")


if __name__ == "__main__":
    unittest.main()
