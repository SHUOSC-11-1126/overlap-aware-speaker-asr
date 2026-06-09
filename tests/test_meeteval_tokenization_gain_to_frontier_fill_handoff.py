from __future__ import annotations

import unittest

from src.meeteval_tokenization_gain_to_frontier_fill_handoff import build_handoff_row


class MeetEvalTokenizationGainToFrontierFillHandoffTest(unittest.TestCase):
    def test_build_handoff_row_when_queue_complete(self) -> None:
        summary = {
            "queue_status": "queue_complete",
            "handoff_status": "tokenization_gain_handoff_ready",
            "adapted_and_aligned_count": "5",
            "case_count": "5",
        }

        row = build_handoff_row(summary)

        self.assertEqual(row["handoff_status"], "tokenization_gain_frontier_fill_handoff_ready")
        self.assertIn("runbook_card", row["handoff_target"])

    def test_build_handoff_row_pending_when_not_complete(self) -> None:
        summary = {"queue_status": "queue_in_progress"}

        row = build_handoff_row(summary)

        self.assertEqual(row["handoff_status"], "tokenization_gain_frontier_fill_handoff_pending")


if __name__ == "__main__":
    unittest.main()
