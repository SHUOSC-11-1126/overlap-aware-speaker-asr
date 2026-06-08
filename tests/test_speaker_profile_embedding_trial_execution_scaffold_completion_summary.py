from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_scaffold_completion_summary import build_completion_row


class SpeakerProfileScaffoldCompletionSummaryTest(unittest.TestCase):
    def test_build_completion_row_marks_queue_complete(self) -> None:
        row = build_completion_row({"readiness_status": "scaffold_ready", "case_id": "NoOverlap"})

        self.assertEqual(row["queue_status"], "queue_complete")


if __name__ == "__main__":
    unittest.main()
