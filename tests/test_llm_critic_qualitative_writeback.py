from __future__ import annotations

import unittest
from unittest.mock import patch

from src.llm_critic_qualitative_writeback import build_fill_row, build_receipt_row


class LlmCriticQualitativeWritebackTest(unittest.TestCase):
    def test_build_receipt_row_marks_qualitative_writeback_complete(self) -> None:
        row = build_receipt_row(
            [
                {"case_id": "LightOverlap"},
                {"case_id": "MidOverlap"},
            ]
        )
        self.assertEqual(row["execution_status"], "qualitative_writeback_complete")
        self.assertIn("verified correction", row["writeback_note"])

    def test_build_fill_row_counts_brief_cases(self) -> None:
        row = build_fill_row([{"case_id": "LightOverlap"}, {"case_id": "MidOverlap"}])
        self.assertEqual(row["brief_case_count"], "2")

    def test_run_qualitative_writeback_requires_ready_state(self) -> None:
        from src.llm_critic_qualitative_writeback import run_qualitative_writeback

        with patch(
            "src.llm_critic_qualitative_writeback.load_go_no_go_summary",
            return_value={"overall_state": "writeback_not_ready"},
        ):
            with self.assertRaises(RuntimeError):
                run_qualitative_writeback()


if __name__ == "__main__":
    unittest.main()
