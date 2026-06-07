from __future__ import annotations

import unittest

from src.llm_critic_review_pass_final import build_final_row, select_queue_row_for_case
from src.llm_critic_review_pass_completion_summary import build_completion_summary_row


class LlmCriticReviewPassFinalTest(unittest.TestCase):
    def test_select_queue_row_for_case_finds_opposite_overlap(self) -> None:
        row = select_queue_row_for_case(
            [
                {"case_id": "NoOverlap", "queue_order": "4"},
                {"case_id": "OppositeOverlap", "queue_order": "5"},
            ],
            "OppositeOverlap",
        )

        self.assertEqual(row["queue_order"], "5")

    def test_build_final_row_records_queue_completion(self) -> None:
        row = build_final_row(
            {"case_id": "OppositeOverlap", "queue_order": "5"},
            {
                "case_id": "OppositeOverlap",
                "review_priority": "high",
                "review_outcome": "Qualitative critic pass recorded for OppositeOverlap; no verified transcript repair was applied.",
            },
            4,
        )

        self.assertIn("gold review queue is now complete", row["final_note"].lower())


class LlmCriticReviewPassCompletionSummaryTest(unittest.TestCase):
    def test_build_completion_summary_row_marks_queue_complete(self) -> None:
        row = build_completion_summary_row(
            [{"pass_status": "review_complete", "case_id": "NoOverlap"}] * 5
        )

        self.assertEqual(row["queue_status"], "queue_complete")
        self.assertEqual(row["pending_count"], "0")


if __name__ == "__main__":
    unittest.main()
