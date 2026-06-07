from __future__ import annotations

import unittest

from src.external_validation_slice_staging_handoff_receipt_scaffold import (
    build_scaffold_receipt_rows,
    build_scaffold_row,
)


class ExternalValidationSliceStagingHandoffReceiptScaffoldTest(unittest.TestCase):
    def test_build_scaffold_row_records_license_blocker(self) -> None:
        row = build_scaffold_row(
            {
                "dataset_name": "AISHELL-4",
                "handoff_status": "staging_handoff_ready",
                "blocker": "license_confirmation_pending",
            }
        )

        self.assertEqual(row["scaffold_status"], "receipt_scaffold_only")
        self.assertEqual(row["blocker"], "license_confirmation_pending")

    def test_build_scaffold_receipt_rows_document_scaffold(self) -> None:
        rows = build_scaffold_receipt_rows({"dataset_name": "AISHELL-4", "blocker": "license_confirmation_pending"})

        self.assertEqual(rows[0]["execution_status"], "receipt_scaffold_complete")


if __name__ == "__main__":
    unittest.main()
