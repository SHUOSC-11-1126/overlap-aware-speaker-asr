from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_receipt_milestone_card import build_milestone_card_row


class SpeakerProfileEmbeddingTrialExecutionReceiptMilestoneCardTest(unittest.TestCase):
    def test_build_milestone_card_row_unlocks_receipt_reopen(self) -> None:
        row = build_milestone_card_row(
            {
                "checkpoint_case": "NoOverlap",
                "completion_signal": "Confirm this bridge before opening results/figures/speaker_profile_embedding_trial_execution_receipt_readiness.md.",
            },
            [
                {
                    "checklist_order": "1",
                    "receipt_target": "results/figures/speaker_profile_embedding_trial_execution_receipt_readiness.md",
                }
            ],
        )

        self.assertEqual(row["next_milestone"], "speaker_profile_receipt_readiness_reopen_ready")
        self.assertIn("receipt_readiness.md", row["unlocks"])
        self.assertEqual(row["remaining_gate_count"], "0")

    def test_build_milestone_card_row_returns_empty_without_checkpoint(self) -> None:
        row = build_milestone_card_row({}, [])

        self.assertEqual(row, {})


if __name__ == "__main__":
    unittest.main()
