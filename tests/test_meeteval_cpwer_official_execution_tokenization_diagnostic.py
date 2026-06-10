from __future__ import annotations

import unittest

from src.meeteval_cpwer_official_execution_tokenization_diagnostic import (
    build_diagnostic_row,
    build_diagnostic_rows,
)


class MeetEvalCpwerOfficialExecutionTokenizationDiagnosticTest(unittest.TestCase):
    def test_build_diagnostic_row_pending_without_official_cpwer(self) -> None:
        row = build_diagnostic_row("NoOverlap", None)
        self.assertEqual(row["case_id"], "NoOverlap")
        self.assertEqual(row["diagnostic_status"], "pending_official_execution")
        self.assertIn("not yet available", row["diagnostic_note"])

    def test_build_diagnostic_row_identifies_tokenization_root_cause(self) -> None:
        row = build_diagnostic_row(
            "NoOverlap",
            {"official_cpwer": "1.5"},
        )
        self.assertEqual(row["root_cause"], "no_whitespace_word_tokenization")
        self.assertEqual(row["diagnostic_status"], "root_cause_identified")

    def test_build_diagnostic_rows_includes_gold_cases(self) -> None:
        rows = build_diagnostic_rows()
        case_ids = {row["case_id"] for row in rows}
        self.assertIn("NoOverlap", case_ids)
        self.assertGreaterEqual(len(rows), 5)


if __name__ == "__main__":
    unittest.main()
