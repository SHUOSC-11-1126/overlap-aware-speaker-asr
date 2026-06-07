from __future__ import annotations

import unittest

from src.llm_critic_review_pass_advance_bridge_checklist import (
    build_bridge_checklist_lines,
    build_bridge_checklist_rows,
)


class LlmCriticReviewPassAdvanceBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_use_advance_row(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "case_id": "LightOverlap",
                "prior_pass_status": "HeavyOverlap review_complete",
            }
        )

        self.assertEqual(rows[0]["case_id"], "LightOverlap")
        self.assertIn("HeavyOverlap review_complete", rows[0]["bridge_note"])

    def test_build_bridge_checklist_lines_render_note(self) -> None:
        lines = build_bridge_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "case_id": "LightOverlap",
                    "prerequisite_artifact": "results/figures/llm_critic_review_pass_advance.md",
                    "receipt_target": "results/figures/llm_critic_review_pass_advance_receipt.md",
                    "checklist_goal": "Verify the second qualitative pass bridge.",
                    "bridge_note": "Queue advanced.",
                    "next_gate": "Confirm this bridge before opening the critic review pass advance receipt target.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# LLM Critic Review Pass Advance Bridge Checklist", rendered)


if __name__ == "__main__":
    unittest.main()
