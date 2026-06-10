from __future__ import annotations

import unittest

from src.llm_critic_review_pass_completion_summary import (
    build_completion_summary_lines,
    build_completion_summary_row,
)


class LlmCriticReviewPassCompletionSummaryTest(unittest.TestCase):
    def _status_row(self, case_id: str, pass_status: str) -> dict[str, str]:
        return {
            "queue_order": "1",
            "case_id": case_id,
            "pass_status": pass_status,
            "review_priority": "high",
            "next_action": "review",
        }

    def test_build_completion_summary_row_marks_queue_complete_when_no_pending(self) -> None:
        row = build_completion_summary_row(
            [self._status_row("NoOverlap", "review_complete")]
        )
        self.assertEqual(row["queue_status"], "queue_complete")
        self.assertEqual(row["completed_count"], "1")
        self.assertIn("qualitative", row["observation"].lower())

    def test_build_completion_summary_row_marks_in_progress_with_pending(self) -> None:
        row = build_completion_summary_row(
            [
                self._status_row("NoOverlap", "review_complete"),
                self._status_row("LightOverlap", "pending_review"),
            ]
        )
        self.assertEqual(row["queue_status"], "queue_in_progress")
        self.assertEqual(row["pending_count"], "1")

    def test_build_completion_summary_lines_renders_markdown_table(self) -> None:
        row = build_completion_summary_row(
            [self._status_row("NoOverlap", "review_complete")]
        )
        lines = build_completion_summary_lines(row)
        self.assertIn("# LLM Critic Review Pass Completion Summary", lines[0])
        self.assertTrue(any("queue_complete" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
