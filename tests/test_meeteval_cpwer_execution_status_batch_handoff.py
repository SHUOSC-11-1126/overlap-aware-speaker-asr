from __future__ import annotations

import unittest

from src.meeteval_cpwer_execution_status_batch_handoff import build_handoff_rows


class MeetEvalCpwerExecutionStatusBatchHandoffTest(unittest.TestCase):
    def test_build_handoff_rows_mark_first_ready_case(self) -> None:
        status_rows = [
            {"case_id": "NoOverlap", "execution_chain_status": "execution_chain_ready"},
            {"case_id": "LightOverlap", "execution_chain_status": "execution_chain_ready"},
        ]
        preflight_rows = [
            {"case_id": "NoOverlap", "hypothesis_source": "separated_whisper"},
            {"case_id": "LightOverlap", "hypothesis_source": "mixed_whisper"},
        ]
        rows = build_handoff_rows(status_rows, preflight_rows)

        self.assertEqual(len(rows), 2)
        ready_rows = [row for row in rows if row["handoff_status"] == "execution_handoff_ready"]
        self.assertEqual(len(ready_rows), 1)
        self.assertEqual(ready_rows[0]["case_id"], "NoOverlap")

    def test_build_handoff_rows_default_to_gold_cases_when_empty(self) -> None:
        rows = build_handoff_rows([], [])

        self.assertEqual(len(rows), 5)


if __name__ == "__main__":
    unittest.main()
