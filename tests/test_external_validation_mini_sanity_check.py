from __future__ import annotations

import unittest

from src.external_validation_license_confirmation import CONFIRMED_LICENSE_STATUS
from src.external_validation_mini_sanity_check import build_check_row, schema_is_valid


class ExternalValidationMiniSanityCheckTest(unittest.TestCase):
    def test_schema_is_valid_requires_speaker_fields(self) -> None:
        self.assertTrue(
            schema_is_valid(
                {
                    "speaker_schema": {
                        "speaker_field": "speaker",
                        "start_field": "start",
                        "end_field": "end",
                        "text_field": "text",
                    }
                }
            )
        )
        self.assertFalse(schema_is_valid({"speaker_schema": {"speaker_field": "speaker"}}))

    def test_build_check_row_metadata_pass_when_license_confirmed(self) -> None:
        row = build_check_row(
            {
                "dataset_name": "AISHELL-4",
                "slice_id": "stub",
                "label": "external/sanity-check",
                "license_status": CONFIRMED_LICENSE_STATUS,
                "audio_path": "missing.wav",
                "reference_path": "missing.json",
                "speaker_schema": {
                    "speaker_field": "speaker",
                    "start_field": "start",
                    "end_field": "end",
                    "text_field": "text",
                },
            }
        )
        self.assertEqual(row["validation_status"], "metadata_only_pass")
        self.assertEqual(row["license_confirmed"], "True")


if __name__ == "__main__":
    unittest.main()
