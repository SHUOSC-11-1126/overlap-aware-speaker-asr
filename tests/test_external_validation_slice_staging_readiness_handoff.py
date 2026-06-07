from __future__ import annotations

import unittest

from src.external_validation_slice_staging_readiness_handoff import (
    build_handoff_receipt_rows,
    build_handoff_row,
)


class ExternalValidationSliceStagingReadinessHandoffTest(unittest.TestCase):
    def test_build_handoff_row_records_license_blocker(self) -> None:
        row = build_handoff_row(
            {
                "dataset_name": "AISHELL-4",
                "readiness_status": "not_ready",
                "blocker": "license_confirmation_pending",
            }
        )

        self.assertEqual(row["dataset_name"], "AISHELL-4")
        self.assertIn("license_confirmation_pending", row["handoff_goal"])

    def test_build_handoff_receipt_rows_document_handoff(self) -> None:
        rows = build_handoff_receipt_rows({"dataset_name": "AISHELL-4"})

        self.assertEqual(rows[0]["execution_status"], "handoff_documented")


if __name__ == "__main__":
    unittest.main()
