from __future__ import annotations

import unittest

from src.external_validation_slice_staging_handoff_receipt_readiness_bridge_checklist import (
    build_bridge_checklist_rows,
)


class ExternalValidationSliceStagingHandoffReceiptReadinessBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_uses_blocker(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "dataset_name": "AISHELL-4",
                "readiness_status": "receipt_ready_to_fill",
                "blocker": "license_confirmation_pending",
            }
        )

        self.assertIn("license_confirmation_pending", rows[0]["bridge_note"])


if __name__ == "__main__":
    unittest.main()
