from __future__ import annotations

import unittest

from src.meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_bridge_checklist import (
    build_bridge_checklist_lines,
    build_bridge_checklist_rows,
)


class MeetEvalCpwerAlignmentDriftSegmentSpeakerCountDiagnosticBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_use_summary(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "case_id": "HeavyOverlap",
                "mismatched_speaker_count": "2",
                "dominant_blocker": "SPEAKER_1 delta=2",
            }
        )

        self.assertEqual(rows[0]["mismatched_speaker_count"], "2")

    def test_build_bridge_checklist_lines_render_note(self) -> None:
        lines = build_bridge_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "case_id": "HeavyOverlap",
                    "mismatched_speaker_count": "2",
                    "prerequisite_artifact": "results/figures/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_summary.md",
                    "receipt_target": "results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic_bridge_checklist.md",
                    "checklist_goal": "Verify the speaker count diagnostic bridge.",
                    "bridge_note": "mismatched_speaker_count=2.",
                    "next_gate": "Confirm this bridge before opening the cpWER segment reconciliation diagnostic bridge checklist target.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn(
            "# MeetEval cpWER Alignment Drift Segment Speaker Count Diagnostic Bridge Checklist",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
