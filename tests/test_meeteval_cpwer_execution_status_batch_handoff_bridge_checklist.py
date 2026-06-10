from __future__ import annotations

import unittest

from src.meeteval_cpwer_execution_status_batch_handoff_bridge_checklist import (
    build_bridge_checklist_lines,
    build_bridge_checklist_rows,
)


class MeetEvalCpwerExecutionStatusBatchHandoffBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_counts_ready_handoffs(self) -> None:
        rows = build_bridge_checklist_rows(
            [
                {
                    "case_id": "NoOverlap",
                    "handoff_status": "execution_handoff_ready",
                },
                {
                    "case_id": "LightOverlap",
                    "handoff_status": "pending",
                },
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["handoff_ready_count"], "1")
        self.assertEqual(rows[0]["handoff_total_count"], "2")
        self.assertIn("NoOverlap", rows[0]["checklist_goal"])
        self.assertIn("official_execution.json", rows[0]["receipt_target"])

    def test_build_bridge_checklist_rows_returns_empty_without_rows(self) -> None:
        self.assertEqual(build_bridge_checklist_rows([]), [])

    def test_build_bridge_checklist_lines_renders_markdown_table(self) -> None:
        rows = build_bridge_checklist_rows(
            [
                {
                    "case_id": "NoOverlap",
                    "handoff_status": "execution_handoff_ready",
                }
            ]
        )
        lines = build_bridge_checklist_lines(rows)

        self.assertIn(
            "# MeetEval cpWER Execution Status Batch Handoff Bridge Checklist",
            lines[0],
        )
        self.assertTrue(any("handoff_ready_count" in line or "| 1 |" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
