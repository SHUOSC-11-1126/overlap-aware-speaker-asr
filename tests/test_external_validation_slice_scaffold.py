from __future__ import annotations

import unittest

from src.external_validation_slice_scaffold import (
    build_aishell4_mapping_stub,
    build_mapping_row,
    build_scaffold_receipt_lines,
    build_scaffold_receipt_rows,
    build_scaffold_summary_lines,
)


class ExternalValidationSliceScaffoldTest(unittest.TestCase):
    def test_build_aishell4_mapping_stub_is_scaffold_only(self) -> None:
        stub = build_aishell4_mapping_stub()

        self.assertEqual(stub["dataset_name"], "AISHELL-4")
        self.assertEqual(stub["mapping_status"], "scaffold_only")
        self.assertEqual(stub["license_status"], "pending_confirmation")
        self.assertEqual(stub["segments"], [])

    def test_build_mapping_row_flattens_stub(self) -> None:
        row = build_mapping_row(build_aishell4_mapping_stub())

        self.assertEqual(row["slice_id"], "aishell4_meeting_excerpt_stub_001")
        self.assertIn("speaker", row["speaker_schema"])

    def test_build_scaffold_receipt_rows_mark_scaffold_complete(self) -> None:
        rows = build_scaffold_receipt_rows(build_mapping_row(build_aishell4_mapping_stub()))

        self.assertEqual(rows[0]["execution_status"], "scaffold_complete")
        self.assertEqual(rows[0]["dataset_name"], "AISHELL-4")
        self.assertIn("has been run yet", rows[0]["writeback_note"].lower())

    def test_build_scaffold_summary_lines_render_note(self) -> None:
        lines = build_scaffold_summary_lines(build_mapping_row(build_aishell4_mapping_stub()))
        rendered = "\n".join(lines)

        self.assertIn("# External Validation Slice Scaffold", rendered)
        self.assertIn("AISHELL-4", rendered)
        self.assertIn("scaffold_only", rendered)

    def test_build_scaffold_receipt_lines_render_receipt(self) -> None:
        lines = build_scaffold_receipt_lines(
            [
                {
                    "execution_status": "scaffold_complete",
                    "slice_scope": "single_short_meeting_excerpt",
                    "dataset_name": "AISHELL-4",
                    "mapping_artifact": "results/tables/external_validation_slice_mapping.json",
                    "license_status": "pending_confirmation",
                    "expected_outputs": "Repo mapping stub and license gate note for the first external slice.",
                    "writeback_note": "External slice scaffold complete; no external benchmark audio or evaluation has been run yet.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("scaffold_complete", rendered)
        self.assertIn("pending_confirmation", rendered)


if __name__ == "__main__":
    unittest.main()
