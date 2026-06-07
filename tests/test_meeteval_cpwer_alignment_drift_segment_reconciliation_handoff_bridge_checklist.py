from __future__ import annotations

import unittest

from src.meeteval_cpwer_alignment_drift_segment_reconciliation_handoff_bridge_checklist import (
    build_bridge_checklist_lines,
    build_bridge_checklist_rows,
)


class MeetEvalCpwerAlignmentDriftSegmentReconciliationHandoffBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_use_handoff(self) -> None:
        rows = build_bridge_checklist_rows(
            {"case_id": "HeavyOverlap", "handoff_status": "reconciliation_handoff_ready"}
        )

        self.assertEqual(rows[0]["case_id"], "HeavyOverlap")

    def test_build_bridge_checklist_lines_render_note(self) -> None:
        lines = build_bridge_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "case_id": "HeavyOverlap",
                    "handoff_status": "reconciliation_handoff_ready",
                    "prerequisite_artifact": "results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_handoff.md",
                    "receipt_target": "results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_scaffold_bridge_checklist.md",
                    "checklist_goal": "Verify the reconciliation handoff bridge.",
                    "bridge_note": "Reconciliation handoff remains reconciliation_handoff_ready.",
                    "next_gate": "Confirm this bridge before opening the cpWER segment reconciliation scaffold bridge checklist target.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn(
            "# MeetEval cpWER Alignment Drift Segment Reconciliation Handoff Bridge Checklist",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
