from __future__ import annotations

import unittest

from src.meeteval_cpwer_tokenization_gain_scorecard_handoff_completion_summary import (
    build_completion_row,
)


class MeetEvalCpwerTokenizationGainScorecardHandoffCompletionSummaryTest(unittest.TestCase):
    def test_build_completion_row_when_handoff_ready(self) -> None:
        handoff = {
            "handoff_status": "tokenization_gain_handoff_ready",
            "adapted_and_aligned_count": "5",
            "case_count": "5",
        }

        row = build_completion_row(handoff)

        self.assertEqual(row["queue_status"], "queue_complete")
        self.assertEqual(row["handoff_status"], "tokenization_gain_handoff_ready")

    def test_build_completion_row_pending_when_handoff_not_ready(self) -> None:
        handoff = {
            "handoff_status": "tokenization_gain_handoff_pending",
            "adapted_and_aligned_count": "3",
            "case_count": "5",
        }

        row = build_completion_row(handoff)

        self.assertEqual(row["queue_status"], "queue_in_progress")


if __name__ == "__main__":
    unittest.main()
