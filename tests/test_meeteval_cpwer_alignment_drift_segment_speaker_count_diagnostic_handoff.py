from __future__ import annotations

import unittest

from src.meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_handoff import (
    build_handoff_receipt_rows,
    build_handoff_row,
)


class MeetEvalCpwerAlignmentDriftSegmentSpeakerCountDiagnosticHandoffTest(unittest.TestCase):
    def test_build_handoff_row_targets_timing_diagnostic(self) -> None:
        row = build_handoff_row(
            {
                "case_id": "HeavyOverlap",
                "mismatched_speaker_count": "2",
                "dominant_blocker": "SPEAKER_1 delta=-1",
            }
        )

        self.assertEqual(row["case_id"], "HeavyOverlap")
        self.assertIn("timing_diagnostic", row["timing_diagnostic_target"])

    def test_build_handoff_receipt_rows_document_handoff(self) -> None:
        rows = build_handoff_receipt_rows({"case_id": "HeavyOverlap"})

        self.assertEqual(rows[0]["execution_status"], "handoff_documented")


if __name__ == "__main__":
    unittest.main()
