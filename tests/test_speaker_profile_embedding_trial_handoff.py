from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_handoff import build_handoff_receipt_rows, build_handoff_row


class SpeakerProfileEmbeddingTrialHandoffTest(unittest.TestCase):
    def test_build_handoff_row_targets_no_overlap_trial(self) -> None:
        row = build_handoff_row(
            {
                "dominant_pattern": "swapped_bias",
                "method_direction": "embedding_or_voiceprint_baseline",
            }
        )

        self.assertEqual(row["trial_case_target"], "NoOverlap")
        self.assertEqual(row["handoff_status"], "embedding_trial_handoff_ready")

    def test_build_handoff_receipt_rows_document_handoff(self) -> None:
        rows = build_handoff_receipt_rows({"method_direction": "embedding_or_voiceprint_baseline"})

        self.assertEqual(rows[0]["execution_status"], "handoff_documented")


if __name__ == "__main__":
    unittest.main()
