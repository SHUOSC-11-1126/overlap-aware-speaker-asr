from __future__ import annotations

import unittest

from src.demo_walkthrough_review_pass_third_continue import (
    build_continue_row,
    select_next_step,
)


class DemoWalkthroughReviewPassThirdContinueTest(unittest.TestCase):
    def test_select_next_step_skips_completed(self) -> None:
        step = select_next_step(
            [
                {"step_id": "1", "focus": "Problem framing"},
                {"step_id": "2", "focus": "Baseline evidence"},
                {"step_id": "3", "focus": "Routing takeaway"},
                {"step_id": "4", "focus": "Frontier breadth"},
                {"step_id": "5", "focus": "Next-step framing"},
            ],
            {"1", "2", "3", "4"},
        )

        self.assertEqual(step["step_id"], "5")

    def test_build_continue_row_records_completed_count(self) -> None:
        row = build_continue_row({"step_id": "5", "focus": "Next-step framing"}, 4)

        self.assertEqual(row["step_id"], "5")
        self.assertEqual(row["completed_step_count"], "4")


if __name__ == "__main__":
    unittest.main()
