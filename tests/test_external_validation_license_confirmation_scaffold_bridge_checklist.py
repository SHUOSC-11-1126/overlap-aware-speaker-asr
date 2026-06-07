from __future__ import annotations

import unittest

from src.external_validation_license_confirmation_scaffold_bridge_checklist import (
    build_bridge_checklist_lines,
    build_bridge_checklist_rows,
)


class ExternalValidationLicenseConfirmationScaffoldBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_use_scaffold(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "dataset_name": "AISHELL-4",
                "confirmation_status": "template_only",
                "license_status": "pending_confirmation",
            }
        )

        self.assertEqual(rows[0]["dataset_name"], "AISHELL-4")
        self.assertIn("template_only", rows[0]["bridge_note"])

    def test_build_bridge_checklist_lines_render_note(self) -> None:
        lines = build_bridge_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "dataset_name": "AISHELL-4",
                    "confirmation_status": "template_only",
                    "prerequisite_artifact": "results/figures/external_validation_license_confirmation_scaffold.md",
                    "receipt_target": "results/figures/external_validation_slice_staging_readiness.md",
                    "checklist_goal": "Verify the license confirmation scaffold bridge.",
                    "bridge_note": "Confirmation remains template_only.",
                    "next_gate": "Confirm this bridge before opening the external slice staging readiness target.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# External Validation License Confirmation Scaffold Bridge Checklist", rendered)


if __name__ == "__main__":
    unittest.main()
