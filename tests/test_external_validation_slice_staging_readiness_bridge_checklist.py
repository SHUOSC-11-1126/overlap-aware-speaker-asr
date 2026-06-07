from __future__ import annotations

import unittest

from src.external_validation_slice_staging_readiness_bridge_checklist import (
    build_bridge_checklist_lines,
    build_bridge_checklist_rows,
)


class ExternalValidationSliceStagingReadinessBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_use_readiness(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "readiness_status": "not_ready",
                "blocker": "license_confirmation_pending",
            }
        )

        self.assertEqual(rows[0]["readiness_status"], "not_ready")
        self.assertIn("license_confirmation_pending", rows[0]["bridge_note"])

    def test_build_bridge_checklist_lines_render_note(self) -> None:
        lines = build_bridge_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "readiness_status": "not_ready",
                    "prerequisite_artifact": "results/figures/external_validation_slice_staging_readiness.md",
                    "receipt_target": "results/figures/external_validation_slice_manifest_bridge_checklist.md",
                    "checklist_goal": "Verify the staging readiness bridge.",
                    "bridge_note": "Readiness remains not_ready.",
                    "next_gate": "Confirm this bridge before opening the slice manifest bridge checklist target.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# External Validation Slice Staging Readiness Bridge Checklist", rendered)


if __name__ == "__main__":
    unittest.main()
