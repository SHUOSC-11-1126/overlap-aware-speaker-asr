from __future__ import annotations

import unittest

from src.speaker_profile_go_no_go_board_handoff_completion_summary_bridge_checklist import (
    build_bridge_checklist_rows,
)


class SpeakerProfileGoNoGoBoardHandoffCompletionSummaryBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_when_queue_complete(self) -> None:
        summary = {
            "queue_status": "queue_complete",
            "handoff_status": "speaker_profile_go_handoff_ready",
            "case_scope": "NoOverlap",
        }

        rows = build_bridge_checklist_rows(summary)

        self.assertEqual(len(rows), 1)
        self.assertIn("execution_scaffold_readiness", rows[0]["receipt_target"])

    def test_build_bridge_checklist_rows_empty_when_summary_missing(self) -> None:
        self.assertEqual(build_bridge_checklist_rows({}), [])


if __name__ == "__main__":
    unittest.main()
