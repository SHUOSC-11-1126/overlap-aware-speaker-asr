from __future__ import annotations

import unittest

from src.meeteval_cpwer_official_execution_alignment_audit_bridge_checklist import (
    build_bridge_checklist_rows as build_alignment_bridge_rows,
)
from src.meeteval_cpwer_official_execution_reconciliation_audit_bridge_checklist import (
    build_bridge_checklist_rows as build_reconciliation_bridge_rows,
)


class MeetEvalCpwerOfficialExecutionAuditBridgeChecklistsTest(unittest.TestCase):
    def test_alignment_bridge_links_drift_audit_to_tokenization_diagnostic(self) -> None:
        rows = build_alignment_bridge_rows(
            [
                {"alignment_status": "moderate_drift"},
                {"alignment_status": "aligned"},
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["drift_case_count"], "1")
        self.assertEqual(rows[0]["total_count"], "2")
        self.assertIn("alignment_audit.md", rows[0]["prerequisite_artifact"])
        self.assertIn("tokenization_diagnostic.md", rows[0]["receipt_target"])

    def test_alignment_bridge_returns_empty_without_rows(self) -> None:
        rows = build_alignment_bridge_rows([])

        self.assertEqual(rows, [])

    def test_reconciliation_bridge_links_audit_to_character_level_evidence(self) -> None:
        rows = build_reconciliation_bridge_rows(
            [
                {"reconciliation_status": "aligned"},
                {"reconciliation_status": "minor_drift"},
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["aligned_count"], "1")
        self.assertEqual(rows[0]["total_count"], "2")
        self.assertIn("reconciliation_audit.md", rows[0]["prerequisite_artifact"])
        self.assertIn("character_level_official_execution.md", rows[0]["receipt_target"])

    def test_reconciliation_bridge_returns_empty_without_rows(self) -> None:
        rows = build_reconciliation_bridge_rows([])

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
