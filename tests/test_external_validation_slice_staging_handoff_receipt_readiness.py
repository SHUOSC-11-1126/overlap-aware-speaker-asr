from __future__ import annotations

import unittest

from src.external_validation_slice_staging_handoff_receipt_readiness import build_readiness_row


class ExternalValidationSliceStagingHandoffReceiptReadinessTest(unittest.TestCase):
    def test_build_readiness_row_marks_ready_when_chain_and_template_pass(self) -> None:
        row = build_readiness_row(
            {
                "dataset_name": "AISHELL-4",
                "execution_chain_status": "execution_chain_ready",
                "blocker": "license_confirmation_pending",
            },
            {"dataset_name": "AISHELL-4", "execution_status": "template_only"},
        )

        self.assertEqual(row["readiness_status"], "receipt_ready_to_fill")

    def test_build_readiness_row_marks_not_ready_when_chain_pending(self) -> None:
        row = build_readiness_row(
            {"execution_chain_status": "execution_chain_in_progress"},
            {"execution_status": "template_only"},
        )

        self.assertEqual(row["readiness_status"], "receipt_not_ready")


if __name__ == "__main__":
    unittest.main()
