from __future__ import annotations

import unittest

from src.speaker_profile_go_no_go_board_handoff_completion_summary import build_completion_row


class SpeakerProfileGoNoGoBoardHandoffCompletionSummaryTest(unittest.TestCase):
    def test_build_completion_row_when_handoff_ready(self) -> None:
        handoff = {
            "handoff_status": "speaker_profile_go_handoff_ready",
            "overall_state": "narrow_execution_ready",
            "go_count": "4",
            "checkpoint_count": "4",
        }

        row = build_completion_row(handoff)

        self.assertEqual(row["queue_status"], "queue_complete")

    def test_build_completion_row_pending_when_handoff_not_ready(self) -> None:
        handoff = {"handoff_status": "speaker_profile_go_handoff_pending"}

        row = build_completion_row(handoff)

        self.assertEqual(row["queue_status"], "queue_in_progress")


if __name__ == "__main__":
    unittest.main()
