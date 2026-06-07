from __future__ import annotations

import unittest

from src.external_validation_license_gate import (
    build_license_gate_lines,
    build_license_gate_receipt_lines,
    build_license_gate_receipt_rows,
    build_license_gate_rows,
)


class ExternalValidationLicenseGateTest(unittest.TestCase):
    def test_build_license_gate_rows_document_preflight_steps(self) -> None:
        rows = build_license_gate_rows(
            {
                "dataset_name": "AISHELL-4",
                "label": "external/sanity-check",
                "license_status": "pending_confirmation",
            }
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["gate_order"], "1")
        self.assertIn("license", rows[0]["gate_step"].lower())

    def test_build_license_gate_lines_render_checklist(self) -> None:
        lines = build_license_gate_lines(
            [
                {
                    "dataset_name": "AISHELL-4",
                    "label": "external/sanity-check",
                    "license_status": "pending_confirmation",
                    "gate_step": "Confirm official AISHELL-4 license terms before staging any local audio.",
                    "gate_order": "1",
                    "gate_note": "Read the official release page and record whether local reuse is permitted for a tiny sanity-check slice.",
                    "next_gate": "Document the license decision in the slice receipt before downloading audio.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# External Validation License Gate", rendered)
        self.assertIn("pending_confirmation", rendered)

    def test_build_license_gate_receipt_rows_mark_gate_documented(self) -> None:
        rows = build_license_gate_receipt_rows(
            {
                "dataset_name": "AISHELL-4",
                "license_status": "pending_confirmation",
            }
        )

        self.assertEqual(rows[0]["execution_status"], "license_gate_documented")
        self.assertIn("blocked", rows[0]["writeback_note"].lower())

    def test_build_license_gate_receipt_lines_render_receipt(self) -> None:
        lines = build_license_gate_receipt_lines(
            [
                {
                    "execution_status": "license_gate_documented",
                    "slice_scope": "single_short_meeting_excerpt",
                    "dataset_name": "AISHELL-4",
                    "license_status": "pending_confirmation",
                    "expected_inputs": "Official AISHELL-4 license terms plus the existing slice mapping stub.",
                    "writeback_note": "License gate checklist documented; external audio staging remains blocked until license confirmation is recorded.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("license_gate_documented", rendered)


if __name__ == "__main__":
    unittest.main()
