from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_handoff_completion_summary_bridge_checklist import (
    build_bridge_checklist_rows,
)


class SpeakerProfileEmbeddingTrialHandoffCompletionSummaryBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_execution_scaffold(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "queue_status": "queue_complete",
                "trial_case_target": "NoOverlap",
            }
        )

        self.assertEqual(rows[0]["queue_status"], "queue_complete")
        self.assertIn("execution_scaffold", rows[0]["receipt_target"])


if __name__ == "__main__":
    unittest.main()
