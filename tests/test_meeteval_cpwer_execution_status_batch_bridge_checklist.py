from __future__ import annotations

import unittest

from src.meeteval_cpwer_execution_status_batch_bridge_checklist import build_bridge_checklist_rows


class MeetEvalCpwerExecutionStatusBatchBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_count_ready_cases(self) -> None:
        rows = build_bridge_checklist_rows(
            [
                {"execution_chain_status": "execution_chain_ready"},
                {"execution_chain_status": "execution_chain_in_progress"},
            ]
        )

        self.assertEqual(rows[0]["execution_chain_ready_count"], "1")
        self.assertEqual(rows[0]["execution_chain_total_count"], "2")


if __name__ == "__main__":
    unittest.main()
