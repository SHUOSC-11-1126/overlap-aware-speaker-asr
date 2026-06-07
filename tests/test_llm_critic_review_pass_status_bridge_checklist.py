from __future__ import annotations

import unittest

from src.llm_critic_review_pass_status_bridge_checklist import (
    build_bridge_checklist_lines,
    build_bridge_checklist_rows,
)


class LlmCriticReviewPassStatusBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_use_summary(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "next_case_id": "MidOverlap",
                "completed_count": "2",
                "pending_count": "3",
            }
        )

        self.assertEqual(rows[0]["next_case_id"], "MidOverlap")
        self.assertIn("completed=2", rows[0]["bridge_note"])

    def test_build_bridge_checklist_lines_render_note(self) -> None:
        lines = build_bridge_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "next_case_id": "MidOverlap",
                    "prerequisite_artifact": "results/figures/llm_critic_review_pass_status.md",
                    "receipt_target": "results/figures/llm_critic_review_pass_next_receipt.md",
                    "checklist_goal": "Verify the review pass status bridge.",
                    "bridge_note": "Status rollup reports completed=2.",
                    "next_gate": "Confirm this bridge before opening the critic review pass next receipt target.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# LLM Critic Review Pass Status Bridge Checklist", rendered)


if __name__ == "__main__":
    unittest.main()
