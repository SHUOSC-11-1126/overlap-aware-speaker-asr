from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_receipt_operator_brief_bridge import (
    build_bridge_row,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptOperatorBriefBridgeTest(unittest.TestCase):
    def test_build_bridge_row_links_brief_to_readiness_target(self) -> None:
        row = build_bridge_row(
            {
                "operator_case": "NoOverlap",
                "operator_status": "receipt_ready_to_fill",
                "operator_target": "results/figures/speaker_profile_embedding_trial_execution_receipt_readiness.md",
            }
        )

        self.assertEqual(row["operator_case"], "NoOverlap")
        self.assertEqual(
            row["receipt_target"],
            "results/figures/speaker_profile_embedding_trial_execution_receipt_readiness.md",
        )
        self.assertIn("receipt_ready_to_fill", row["bridge_note"])

    def test_build_bridge_row_returns_empty_without_brief(self) -> None:
        row = build_bridge_row({})

        self.assertEqual(row, {})


if __name__ == "__main__":
    unittest.main()
