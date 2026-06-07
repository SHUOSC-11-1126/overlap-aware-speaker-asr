from __future__ import annotations

import unittest

from src.meeteval_cpwer_execution_preflight_batch import build_preflight_batch_rows


class MeetEvalCpwerExecutionPreflightBatchTest(unittest.TestCase):
    def test_build_preflight_batch_rows_covers_all_gold_cases(self) -> None:
        rows = build_preflight_batch_rows({})

        self.assertEqual(len(rows), 5)
        case_ids = {row["case_id"] for row in rows}
        self.assertIn("NoOverlap", case_ids)
        self.assertIn("HeavyOverlap", case_ids)


if __name__ == "__main__":
    unittest.main()
