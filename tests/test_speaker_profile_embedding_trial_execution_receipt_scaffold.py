from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_receipt_scaffold import (
    build_scaffold_receipt_rows,
    build_scaffold_row,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptScaffoldTest(unittest.TestCase):
    def test_build_scaffold_row_records_receipt_scaffold_only(self) -> None:
        row = build_scaffold_row(
            {
                "case_id": "NoOverlap",
                "preflight_pass": True,
                "method_direction": "embedding_or_voiceprint_baseline",
                "swapped_bias_detected": True,
            }
        )

        self.assertEqual(row["scaffold_status"], "receipt_scaffold_only")
        self.assertEqual(row["swapped_bias_detected"], "True")

    def test_build_scaffold_receipt_rows_document_scaffold(self) -> None:
        rows = build_scaffold_receipt_rows({"case_id": "NoOverlap", "preflight_pass": "True"})

        self.assertEqual(rows[0]["execution_status"], "receipt_scaffold_complete")


if __name__ == "__main__":
    unittest.main()
