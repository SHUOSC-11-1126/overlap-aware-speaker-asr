from __future__ import annotations

import unittest

from src.speaker_profile_go_no_go_board_handoff_bridge_checklist import build_bridge_checklist_rows


class SpeakerProfileGoNoGoBoardHandoffBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_when_handoff_ready(self) -> None:
        handoff = {
            "handoff_status": "speaker_profile_go_handoff_ready",
            "overall_state": "narrow_execution_ready",
            "case_scope": "NoOverlap",
        }

        rows = build_bridge_checklist_rows(handoff)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["handoff_status"], "speaker_profile_go_handoff_ready")

    def test_build_bridge_checklist_rows_empty_when_handoff_missing(self) -> None:
        self.assertEqual(build_bridge_checklist_rows({}), [])


if __name__ == "__main__":
    unittest.main()
