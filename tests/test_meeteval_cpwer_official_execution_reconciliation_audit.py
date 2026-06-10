from __future__ import annotations

import unittest

from src.meeteval_cpwer_official_execution_reconciliation_audit import (
    build_reconciliation_lines,
    build_reconciliation_rows,
)


class MeetEvalCpwerOfficialExecutionReconciliationAuditTest(unittest.TestCase):
    def test_build_reconciliation_rows_classifies_aligned_cases(self) -> None:
        rows = build_reconciliation_rows(
            [
                {
                    "case_id": "NoOverlap",
                    "official_cpwer": "0.12",
                }
            ],
            {"NoOverlap": "0.12"},
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["reconciliation_status"], "aligned")
        self.assertEqual(rows[0]["reconciliation_delta"], "0.0")

    def test_build_reconciliation_rows_handles_missing_character_cpwer(self) -> None:
        rows = build_reconciliation_rows(
            [{"case_id": "NoOverlap", "official_cpwer": ""}],
            {"NoOverlap": "0.12"},
        )
        self.assertIn("not yet available", rows[0]["audit_note"])

    def test_build_reconciliation_lines_includes_summary_counts(self) -> None:
        rows = build_reconciliation_rows(
            [
                {"case_id": "NoOverlap", "official_cpwer": "0.10"},
                {"case_id": "LightOverlap", "official_cpwer": "0.20"},
            ],
            {"NoOverlap": "0.10", "LightOverlap": "0.25"},
        )
        lines = build_reconciliation_lines(rows)
        self.assertIn("# MeetEval cpWER Official Execution Reconciliation Audit", lines[0])
        self.assertTrue(any("aligned" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
