from __future__ import annotations

import unittest

from src.llm_critic_review_pass_bridge_checklist import (
    build_bridge_checklist_lines,
    build_bridge_checklist_rows,
)


class LlmCriticReviewPassBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_use_review_pass(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "case_id": "HeavyOverlap",
                "review_priority": "high",
            }
        )

        self.assertEqual(rows[0]["case_id"], "HeavyOverlap")
        self.assertIn("HeavyOverlap", rows[0]["checklist_goal"])

    def test_build_bridge_checklist_lines_render_note(self) -> None:
        lines = build_bridge_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "case_id": "HeavyOverlap",
                    "prerequisite_artifact": "results/figures/llm_critic_review_pass.md",
                    "receipt_target": "results/figures/llm_critic_review_receipt.md",
                    "checklist_goal": "Verify the critic review pass bridge for HeavyOverlap.",
                    "bridge_note": "Open the review pass note first.",
                    "next_gate": "Confirm this bridge before opening the critic review receipt target.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# LLM Critic Review Pass Bridge Checklist", rendered)
        self.assertIn("HeavyOverlap", rendered)


if __name__ == "__main__":
    unittest.main()
