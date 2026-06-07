from __future__ import annotations

import unittest

from src.external_validation_slice_manifest_bridge_checklist import (
    build_bridge_checklist_lines,
    build_bridge_checklist_rows,
)


class ExternalValidationSliceManifestBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_use_manifest(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "dataset_name": "AISHELL-4",
                "staging_status": "blocked_by_license_gate",
            }
        )

        self.assertEqual(rows[0]["dataset_name"], "AISHELL-4")
        self.assertIn("blocked_by_license_gate", rows[0]["bridge_note"])

    def test_build_bridge_checklist_lines_render_note(self) -> None:
        lines = build_bridge_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "dataset_name": "AISHELL-4",
                    "prerequisite_artifact": "results/figures/external_validation_slice_manifest.md",
                    "receipt_target": "results/figures/external_validation_slice_manifest_receipt.md",
                    "checklist_goal": "Verify the external slice manifest bridge for AISHELL-4.",
                    "bridge_note": "Open the slice manifest first.",
                    "next_gate": "Confirm this bridge before opening the slice manifest receipt target.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# External Validation Slice Manifest Bridge Checklist", rendered)
        self.assertIn("AISHELL-4", rendered)


if __name__ == "__main__":
    unittest.main()
