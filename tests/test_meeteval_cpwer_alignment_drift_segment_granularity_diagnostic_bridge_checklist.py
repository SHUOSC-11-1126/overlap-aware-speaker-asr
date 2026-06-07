from __future__ import annotations

import unittest

from src.meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_bridge_checklist import (
    build_bridge_checklist_rows,
)


class MeetEvalCpwerAlignmentDriftSegmentGranularityDiagnosticBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_timing_handoff_bridge(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "case_id": "HeavyOverlap",
                "mismatched_speaker_count": "2",
                "dominant_blocker": "SPEAKER_1 delta=0.500s",
            }
        )

        self.assertEqual(rows[0]["case_id"], "HeavyOverlap")
        self.assertIn("timing_diagnostic_handoff_bridge", rows[0]["receipt_target"])


if __name__ == "__main__":
    unittest.main()
