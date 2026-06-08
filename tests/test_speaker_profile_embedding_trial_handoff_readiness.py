from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_handoff_readiness import build_readiness_row


class SpeakerProfileEmbeddingTrialHandoffReadinessTest(unittest.TestCase):
    def test_build_readiness_row_marks_handoff_ready(self) -> None:
        row = build_readiness_row(
            {"queue_status": "queue_complete"},
            {
                "handoff_status": "embedding_trial_handoff_ready",
                "trial_case_target": "NoOverlap",
                "method_direction": "embedding_or_voiceprint_baseline",
            },
        )

        self.assertEqual(row["readiness_status"], "handoff_ready")
        self.assertEqual(row["trial_case_target"], "NoOverlap")


if __name__ == "__main__":
    unittest.main()
