from __future__ import annotations

import unittest

from src.demo_storyboard_review_pass_advance_bridge_checklist import build_bridge_checklist_rows


class DemoStoryboardReviewPassAdvanceBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_third_card(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "card_index": "2",
                "card_title": "Pipeline",
                "prior_card_status": "Problem review_complete",
            }
        )

        self.assertEqual(rows[0]["card_title"], "Pipeline")
        self.assertIn("third", rows[0]["next_gate"].lower())


if __name__ == "__main__":
    unittest.main()
