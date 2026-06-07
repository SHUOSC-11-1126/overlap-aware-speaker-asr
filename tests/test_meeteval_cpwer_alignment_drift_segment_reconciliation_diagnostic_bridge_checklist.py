from __future__ import annotations

import unittest

from src.meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic_bridge_checklist import (
    build_bridge_checklist_lines,
    build_bridge_checklist_rows,
)


class MeetEvalCpwerAlignmentDriftSegmentReconciliationDiagnosticBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_use_diagnostic(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "case_id": "HeavyOverlap",
                "reconciliation_pass": False,
                "speaker_segment_count_match": False,
            }
        )

        self.assertEqual(rows[0]["case_id"], "HeavyOverlap")
        self.assertEqual(rows[0]["reconciliation_status"], "reconciliation_diagnostic_complete")

    def test_build_bridge_checklist_lines_render_note(self) -> None:
        lines = build_bridge_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "case_id": "HeavyOverlap",
                    "reconciliation_status": "reconciliation_diagnostic_complete",
                    "prerequisite_artifact": "results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic.md",
                    "receipt_target": "results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_handoff.md",
                    "checklist_goal": "Verify the reconciliation diagnostic bridge.",
                    "bridge_note": "Reconciliation status=reconciliation_diagnostic_complete.",
                    "next_gate": "Confirm this bridge before opening the cpWER segment reconciliation handoff target.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn(
            "# MeetEval cpWER Alignment Drift Segment Reconciliation Diagnostic Bridge Checklist",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
