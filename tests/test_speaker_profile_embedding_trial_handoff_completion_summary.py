from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_handoff_completion_summary import build_completion_row


class SpeakerProfileEmbeddingTrialHandoffCompletionSummaryTest(unittest.TestCase):
    def test_build_completion_row_marks_queue_complete_when_ready(self) -> None:
        row = build_completion_row(
            {
                "readiness_status": "handoff_ready",
                "trial_case_target": "NoOverlap",
                "method_direction": "embedding_or_voiceprint_baseline",
            },
            {},
        )

        self.assertEqual(row["queue_status"], "queue_complete")


if __name__ == "__main__":
    unittest.main()
