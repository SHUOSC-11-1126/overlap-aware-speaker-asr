from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_receipt_operator_brief import (
    build_operator_brief_row,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptOperatorBriefTest(unittest.TestCase):
    def test_build_operator_brief_row_targets_readiness_rollup(self) -> None:
        row = build_operator_brief_row(
            {
                "case_id": "NoOverlap",
                "readiness_status": "receipt_ready_to_fill",
                "receipt_template_status": "template_only",
                "receipt_target": "results/figures/speaker_profile_embedding_trial_execution_receipt_readiness.md",
            }
        )

        self.assertEqual(row["operator_case"], "NoOverlap")
        self.assertEqual(row["operator_status"], "receipt_ready_to_fill")
        self.assertIn("receipt_readiness.md", row["operator_target"])
        self.assertIn("template_only", row["operator_note"])

    def test_build_operator_brief_row_returns_empty_without_bridge_row(self) -> None:
        row = build_operator_brief_row({})

        self.assertEqual(row, {})


if __name__ == "__main__":
    unittest.main()
