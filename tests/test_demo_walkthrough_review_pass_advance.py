from __future__ import annotations

import unittest

from src.demo_walkthrough_review_pass_advance import (
    build_advance_row,
    select_next_step,
)


class DemoWalkthroughReviewPassAdvanceTest(unittest.TestCase):
    def test_select_next_step_skips_completed(self) -> None:
        step = select_next_step(
            [
                {"step_id": "1", "focus": "Problem framing"},
                {"step_id": "2", "focus": "Baseline evidence"},
            ],
            "1",
        )

        self.assertEqual(step["step_id"], "2")

    def test_build_advance_row_records_prior_step(self) -> None:
        row = build_advance_row({"step_id": "2", "focus": "Baseline evidence"}, "1")

        self.assertEqual(row["step_id"], "2")
        self.assertIn("1 review_complete", row["prior_step_status"])


if __name__ == "__main__":
    unittest.main()
