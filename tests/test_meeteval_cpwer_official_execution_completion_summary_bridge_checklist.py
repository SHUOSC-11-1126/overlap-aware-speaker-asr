from __future__ import annotations

import unittest

from src.meeteval_cpwer_official_execution_completion_summary_bridge_checklist import (
    build_bridge_checklist_lines,
    build_bridge_checklist_rows,
)


class MeetEvalCpwerOfficialExecutionCompletionSummaryBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_uses_queue_status(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "queue_status": "queue_complete",
                "complete_count": "5",
                "total_count": "5",
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["queue_status"], "queue_complete")
        self.assertEqual(rows[0]["complete_count"], "5")
        self.assertEqual(rows[0]["total_count"], "5")
        self.assertIn("alignment_audit.md", rows[0]["receipt_target"])

    def test_build_bridge_checklist_rows_returns_empty_without_summary(self) -> None:
        self.assertEqual(build_bridge_checklist_rows({}), [])

    def test_build_bridge_checklist_lines_renders_markdown_table(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "queue_status": "queue_in_progress",
                "complete_count": "2",
                "total_count": "5",
            }
        )
        lines = build_bridge_checklist_lines(rows)

        self.assertIn(
            "# MeetEval cpWER Official Execution Completion Summary Bridge Checklist",
            lines[0],
        )
        self.assertTrue(any("queue_in_progress" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
