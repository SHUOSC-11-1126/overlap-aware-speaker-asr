from __future__ import annotations

import unittest

from src.speaker_profile_go_no_go_board_bridge_checklist import build_bridge_checklist_rows


class SpeakerProfileGoNoGoBoardBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_when_narrow_execution_ready(self) -> None:
        summary = {
            "overall_state": "narrow_execution_ready",
            "go_count": "4",
            "checkpoint_count": "4",
            "case_scope": "NoOverlap",
        }

        rows = build_bridge_checklist_rows(summary)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["overall_state"], "narrow_execution_ready")

    def test_build_bridge_checklist_rows_empty_when_summary_missing(self) -> None:
        self.assertEqual(build_bridge_checklist_rows({}), [])


if __name__ == "__main__":
    unittest.main()
