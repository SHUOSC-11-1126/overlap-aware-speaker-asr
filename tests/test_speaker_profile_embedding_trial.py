from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial import build_trial_receipt_rows, build_trial_row


class SpeakerProfileEmbeddingTrialTest(unittest.TestCase):
    def test_build_trial_row_uses_handoff_case_target(self) -> None:
        row = build_trial_row(
            {"trial_case_target": "NoOverlap", "method_direction": "embedding_or_voiceprint_baseline"},
            {"direct_profile_score": "0.5", "swapped_profile_score": "0.3", "profile_confidence_gap": "0.2"},
        )

        self.assertEqual(row["case_id"], "NoOverlap")
        self.assertEqual(row["trial_status"], "scaffold_only")

    def test_build_trial_receipt_rows_document_scaffold(self) -> None:
        rows = build_trial_receipt_rows({"case_id": "NoOverlap", "method_direction": "embedding_or_voiceprint_baseline"})

        self.assertEqual(rows[0]["execution_status"], "trial_scaffold_complete")


if __name__ == "__main__":
    unittest.main()
