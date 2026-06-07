from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_scaffold import (
    build_execution_scaffold_row,
    build_scaffold_receipt_rows,
)


class SpeakerProfileEmbeddingTrialExecutionScaffoldTest(unittest.TestCase):
    def test_build_execution_scaffold_row_records_execution_scaffold(self) -> None:
        row = build_execution_scaffold_row(
            {
                "case_id": "NoOverlap",
                "method_direction": "embedding_or_voiceprint_baseline",
                "trial_status": "scaffold_only",
                "profile_confidence_gap": "0.15",
            }
        )

        self.assertEqual(row["case_id"], "NoOverlap")
        self.assertEqual(row["scaffold_status"], "execution_scaffold_only")

    def test_build_scaffold_receipt_rows_document_execution_scaffold(self) -> None:
        rows = build_scaffold_receipt_rows({"case_id": "NoOverlap", "method_direction": "embedding_or_voiceprint_baseline"})

        self.assertEqual(rows[0]["execution_status"], "execution_scaffold_complete")


if __name__ == "__main__":
    unittest.main()
