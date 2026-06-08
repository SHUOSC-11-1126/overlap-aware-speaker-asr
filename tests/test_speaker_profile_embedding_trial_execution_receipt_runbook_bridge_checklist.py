from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_receipt_runbook_bridge_checklist import (
    build_bridge_checklist_rows,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptRunbookBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_links_runbook_to_readiness_target(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "recommended_case": "NoOverlap",
                "receipt_target": "results/figures/speaker_profile_embedding_trial_execution_receipt_readiness.md",
                "runbook_note": "Start with NoOverlap.",
            }
        )

        self.assertEqual(rows[0]["recommended_case"], "NoOverlap")
        self.assertIn("receipt_readiness.md", rows[0]["receipt_target"])
        self.assertIn("Confirm this bridge", rows[0]["next_gate"])

    def test_build_bridge_checklist_rows_returns_empty_without_runbook(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
