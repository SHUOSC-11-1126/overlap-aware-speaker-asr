from __future__ import annotations

import unittest

from src.external_validation_slice_staging_handoff_receipt_scaffold_bridge_checklist import (
    build_bridge_checklist_rows,
)


class ExternalValidationSliceStagingHandoffReceiptScaffoldBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_uses_scaffold_fields(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "dataset_name": "AISHELL-4",
                "scaffold_status": "receipt_scaffold_only",
                "blocker": "license_confirmation_pending",
            }
        )

        self.assertEqual(rows[0]["dataset_name"], "AISHELL-4")
        self.assertIn("license_confirmation_pending", rows[0]["bridge_note"])

    def test_build_bridge_checklist_rows_defaults_dataset_name(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows[0]["dataset_name"], "AISHELL-4")


if __name__ == "__main__":
    unittest.main()
