from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_receipt_status_preflight_bridge_checklist import (
    build_bridge_checklist_rows,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptStatusPreflightBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_status_rollup(self) -> None:
        rows = build_bridge_checklist_rows(
            [
                {
                    "current_case": "NoOverlap",
                    "next_gate": "Confirm this bridge before opening results/figures/speaker_profile_embedding_trial_execution_receipt_readiness.md.",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["current_case"], "NoOverlap")
        self.assertIn("speaker_profile_embedding_trial_execution_status.md", rows[0]["receipt_target"])
        self.assertIn("receipt_readiness.md", rows[0]["bridge_note"])

    def test_build_bridge_checklist_rows_returns_empty_without_dashboard_bridge(self) -> None:
        rows = build_bridge_checklist_rows([])

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
