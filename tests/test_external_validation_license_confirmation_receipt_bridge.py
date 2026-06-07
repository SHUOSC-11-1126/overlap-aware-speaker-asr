from __future__ import annotations

import unittest

from src.external_validation_license_confirmation_receipt_bridge import (
    build_bridge_lines,
    build_bridge_rows,
)


class ExternalValidationLicenseConfirmationReceiptBridgeTest(unittest.TestCase):
    def test_build_bridge_rows_use_scaffold(self) -> None:
        rows = build_bridge_rows(
            {
                "dataset_name": "AISHELL-4",
                "confirmation_status": "template_only",
                "license_status": "pending_confirmation",
            }
        )

        self.assertEqual(rows[0]["dataset_name"], "AISHELL-4")

    def test_build_bridge_lines_render_note(self) -> None:
        lines = build_bridge_lines(
            [
                {
                    "bridge_order": "1",
                    "dataset_name": "AISHELL-4",
                    "confirmation_status": "template_only",
                    "license_status": "pending_confirmation",
                    "prerequisite_artifact": "results/figures/external_validation_license_confirmation_scaffold_bridge_checklist.md",
                    "receipt_target": "results/figures/external_validation_slice_receipt.md",
                    "bridge_goal": "Connect the license confirmation scaffold bridge to the slice receipt.",
                    "bridge_note": "Confirmation remains template_only.",
                    "next_gate": "Confirm this bridge before opening the external slice receipt target.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# External Validation License Confirmation Receipt Bridge", rendered)


if __name__ == "__main__":
    unittest.main()
