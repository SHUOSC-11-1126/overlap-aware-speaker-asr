from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_receipt_phase_checkpoint_card import (
    build_phase_checkpoint_row,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptPhaseCheckpointCardTest(unittest.TestCase):
    def test_build_phase_checkpoint_row_uses_runbook_completion_signal(self) -> None:
        row = build_phase_checkpoint_row(
            {
                "recommended_case": "NoOverlap",
                "recommended_action": "Reopen readiness target for NoOverlap.",
                "completion_signal": "Confirm this bridge before opening results/figures/speaker_profile_embedding_trial_execution_receipt_readiness.md.",
            }
        )

        self.assertEqual(row["checkpoint_case"], "NoOverlap")
        self.assertIn("NoOverlap", row["checkpoint_action"])
        self.assertIn("receipt_readiness.md", row["completion_signal"])

    def test_build_phase_checkpoint_row_returns_empty_without_runbook(self) -> None:
        row = build_phase_checkpoint_row({})

        self.assertEqual(row, {})


if __name__ == "__main__":
    unittest.main()
