from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_receipt_milestone_bridge_checklist import (
    build_bridge_checklist_rows,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptMilestoneBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_links_milestone_to_readiness_target(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "next_milestone": "speaker_profile_receipt_readiness_reopen_ready",
                "unlocks": "Reopen results/figures/speaker_profile_embedding_trial_execution_receipt_readiness.md for NoOverlap after the current checkpoint gate closes.",
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["next_milestone"], "speaker_profile_receipt_readiness_reopen_ready")
        self.assertIn("receipt_readiness.md", rows[0]["receipt_target"])
        self.assertIn("NoOverlap", rows[0]["bridge_note"])

    def test_build_bridge_checklist_rows_returns_empty_without_milestone(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
