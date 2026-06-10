from __future__ import annotations

import unittest

from src.meeteval_cpwer_official_execution_bridge_checklist import (
    build_bridge_checklist_lines,
    build_bridge_checklist_rows,
)


class MeetEvalCpwerOfficialExecutionBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_counts_complete_executions(self) -> None:
        rows = build_bridge_checklist_rows(
            [
                {
                    "case_id": "NoOverlap",
                    "execution_status": "official_cpwer_narrow_dry_run_complete",
                },
                {
                    "case_id": "LightOverlap",
                    "execution_status": "pending",
                },
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["complete_count"], "1")
        self.assertEqual(rows[0]["total_count"], "2")
        self.assertIn("NoOverlap", rows[0]["checklist_goal"])
        self.assertIn("execution_receipt.json", rows[0]["receipt_target"])

    def test_build_bridge_checklist_rows_returns_empty_without_rows(self) -> None:
        self.assertEqual(build_bridge_checklist_rows([]), [])

    def test_build_bridge_checklist_lines_renders_markdown_table(self) -> None:
        rows = build_bridge_checklist_rows(
            [
                {
                    "case_id": "NoOverlap",
                    "execution_status": "official_cpwer_narrow_dry_run_complete",
                }
            ]
        )
        lines = build_bridge_checklist_lines(rows)

        self.assertIn("# MeetEval cpWER Official Execution Bridge Checklist", lines[0])
        self.assertTrue(any("official_cpwer_narrow_dry_run_complete" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
