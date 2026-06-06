from __future__ import annotations

import unittest

from src.external_validation_candidates import (
    build_external_validation_candidate_lines,
    build_external_validation_candidate_rows,
)


class ExternalValidationCandidatesTest(unittest.TestCase):
    def test_build_external_validation_candidate_rows_cover_named_datasets(self) -> None:
        rows = build_external_validation_candidate_rows()

        by_name = {row["dataset_name"]: row for row in rows}

        self.assertIn("AISHELL-4", by_name)
        self.assertIn("AliMeeting", by_name)
        self.assertIn("AMI", by_name)
        self.assertIn("LibriCSS", by_name)
        self.assertEqual(by_name["AISHELL-4"]["label"], "external/sanity-check")
        self.assertIn("license", by_name["AISHELL-4"]["license_note"].lower())
        self.assertIn("overlap", by_name["LibriCSS"]["fit_note"].lower())

    def test_build_external_validation_candidate_lines_render_summary(self) -> None:
        lines = build_external_validation_candidate_lines(
            [
                {
                    "dataset_name": "AISHELL-4",
                    "label": "external/sanity-check",
                    "source_note": "Official AISHELL-4 release page.",
                    "license_note": "Check the official license before use.",
                    "fit_note": "Multi-speaker meeting data with realistic overlap.",
                    "first_preprocessing_step": "Map one small subset into the repository speaker-reference format.",
                    "next_action": "Confirm license and select a tiny sanity-check subset.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# External Validation Candidates", rendered)
        self.assertIn("AISHELL-4", rendered)
        self.assertIn("external/sanity-check", rendered)
        self.assertIn("Confirm license", rendered)


if __name__ == "__main__":
    unittest.main()
