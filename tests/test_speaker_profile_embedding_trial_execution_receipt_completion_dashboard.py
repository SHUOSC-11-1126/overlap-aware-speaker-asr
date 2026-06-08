from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_receipt_completion_dashboard import (
    build_dashboard_row,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptCompletionDashboardTest(unittest.TestCase):
    def test_build_dashboard_row_summarizes_receipt_state(self) -> None:
        row = build_dashboard_row(
            {
                "operator_case": "NoOverlap",
                "operator_status": "receipt_ready_to_fill",
            },
            {
                "next_milestone": "speaker_profile_receipt_readiness_reopen_ready",
                "remaining_gate_count": "0",
            },
        )

        self.assertEqual(row["current_case"], "NoOverlap")
        self.assertEqual(row["next_milestone"], "speaker_profile_receipt_readiness_reopen_ready")
        self.assertEqual(row["remaining_gate_count"], "0")
        self.assertEqual(row["dominant_blocker"], "receipt_template_fill_pending")

    def test_build_dashboard_row_returns_empty_without_inputs(self) -> None:
        row = build_dashboard_row({}, {})

        self.assertEqual(row, {})


if __name__ == "__main__":
    unittest.main()
