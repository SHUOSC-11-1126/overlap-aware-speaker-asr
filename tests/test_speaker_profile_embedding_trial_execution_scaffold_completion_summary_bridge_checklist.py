from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_scaffold_completion_summary_bridge_checklist import (
    build_bridge_checklist_rows,
)


class SpeakerProfileScaffoldCompletionSummaryBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_execution_handoff(self) -> None:
        rows = build_bridge_checklist_rows({"queue_status": "queue_complete", "case_id": "NoOverlap"})

        self.assertEqual(rows[0]["queue_status"], "queue_complete")
        self.assertIn("execution_handoff", rows[0]["receipt_target"])


if __name__ == "__main__":
    unittest.main()
