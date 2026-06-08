from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_receipt_phase_checkpoint_bridge_checklist import (
    build_bridge_checklist_rows,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptPhaseCheckpointBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_links_checkpoint_to_readiness_target(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "checkpoint_case": "NoOverlap",
                "completion_signal": "Confirm this bridge before opening results/figures/speaker_profile_embedding_trial_execution_receipt_readiness.md.",
                "checkpoint_note": "Phase checkpoint note.",
            }
        )

        self.assertEqual(rows[0]["checkpoint_case"], "NoOverlap")
        self.assertIn("receipt_readiness.md", rows[0]["receipt_target"])
        self.assertIn("Confirm this bridge", rows[0]["next_gate"])

    def test_build_bridge_checklist_rows_returns_empty_without_checkpoint(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
