from __future__ import annotations

import unittest

from src.speaker_profile_go_no_go_board_handoff import build_handoff_row


class SpeakerProfileGoNoGoBoardHandoffTest(unittest.TestCase):
    def test_build_handoff_row_when_narrow_execution_ready(self) -> None:
        summary = {
            "overall_state": "narrow_execution_ready",
            "go_count": "4",
            "checkpoint_count": "4",
            "case_scope": "NoOverlap",
        }

        row = build_handoff_row(summary)

        self.assertEqual(row["handoff_status"], "speaker_profile_go_handoff_ready")
        self.assertIn("execution_preflight_readiness", row["handoff_target"])

    def test_build_handoff_row_pending_when_not_ready(self) -> None:
        summary = {
            "overall_state": "execution_not_ready",
            "go_count": "2",
            "checkpoint_count": "4",
            "case_scope": "NoOverlap",
        }

        row = build_handoff_row(summary)

        self.assertEqual(row["handoff_status"], "speaker_profile_go_handoff_pending")


if __name__ == "__main__":
    unittest.main()
