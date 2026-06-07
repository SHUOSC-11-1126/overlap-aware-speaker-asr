from __future__ import annotations

import unittest

from src.llm_critic_review_pass_advance import (
    build_advance_row,
    select_next_queue_row,
)


class LlmCriticReviewPassAdvanceTest(unittest.TestCase):
    def test_select_next_queue_row_skips_completed_case(self) -> None:
        row = select_next_queue_row(
            [
                {"case_id": "HeavyOverlap", "queue_order": "1"},
                {"case_id": "LightOverlap", "queue_order": "2"},
            ],
            "HeavyOverlap",
        )

        self.assertEqual(row["case_id"], "LightOverlap")

    def test_build_advance_row_records_prior_pass(self) -> None:
        row = build_advance_row(
            {"case_id": "LightOverlap", "queue_order": "2"},
            {
                "case_id": "LightOverlap",
                "review_priority": "high",
                "review_outcome": "Qualitative critic pass recorded for LightOverlap; no verified transcript repair was applied.",
            },
            "HeavyOverlap",
        )

        self.assertEqual(row["case_id"], "LightOverlap")
        self.assertIn("HeavyOverlap review_complete", row["prior_pass_status"])


if __name__ == "__main__":
    unittest.main()
