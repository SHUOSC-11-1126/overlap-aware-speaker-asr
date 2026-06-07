from __future__ import annotations

import unittest

from src.meeteval_cpwer_execution_status_bridge_checklist import build_bridge_checklist_rows


class MeetEvalCpwerExecutionStatusBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_uses_chain_ready_status(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "case_id": "NoOverlap",
                "execution_chain_status": "execution_chain_ready",
                "preflight_pass": "True",
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["execution_chain_status"], "execution_chain_ready")
        self.assertIn("NoOverlap", rows[0]["checklist_goal"])

    def test_build_bridge_checklist_rows_defaults_case_id(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows[0]["case_id"], "NoOverlap")


if __name__ == "__main__":
    unittest.main()
