from __future__ import annotations

import unittest

from src.external_validation_staging_execution_receipt_fill import (
    build_filled_receipt_rows,
    build_fill_row,
)


class ExternalValidationStagingExecutionReceiptFillTest(unittest.TestCase):
    def test_build_filled_receipt_rows_mark_audio_excerpt_staged(self) -> None:
        rows = build_filled_receipt_rows(
            {"dataset_name": "AISHELL-4", "slice_id": "stub", "result_label": "external/sanity-check"},
            {
                "audio_path": "resources/external_sanity_check/aishell4/meeting_excerpt_stub_001.wav",
                "reference_path": "resources/external_sanity_check/aishell4/meeting_excerpt_stub_001_reference.json",
                "staging_status": "audio_excerpt_staged",
            },
        )
        self.assertEqual(rows[0]["execution_status"], "audio_excerpt_staged")
        self.assertEqual(rows[0]["blocker"], "none_documented")

    def test_fill_execution_receipt_requires_staged_audio(self) -> None:
        from unittest.mock import patch

        from src.external_validation_staging_execution_receipt_fill import fill_execution_receipt

        with patch("src.external_validation_staging_execution_receipt_fill.mini_check_audio_ready", return_value=False):
            with self.assertRaises(RuntimeError):
                fill_execution_receipt()


if __name__ == "__main__":
    unittest.main()
