from __future__ import annotations

import unittest

from src.meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic import (
    build_diagnostic_receipt_row,
    count_segments_per_speaker,
    run_reconciliation_diagnostic,
    speaker_segment_counts_match,
)


class MeetEvalCpwerAlignmentDriftSegmentReconciliationDiagnosticTest(unittest.TestCase):
    def test_count_segments_per_speaker(self) -> None:
        counts = count_segments_per_speaker(
            [
                {"speaker": "SPEAKER_1"},
                {"speaker": "SPEAKER_2"},
                {"speaker": "SPEAKER_1"},
            ]
        )

        self.assertEqual(counts["SPEAKER_1"], 2)
        self.assertEqual(counts["SPEAKER_2"], 1)

    def test_speaker_segment_counts_match_detects_mismatch(self) -> None:
        matched = speaker_segment_counts_match(
            [{"speaker": "SPEAKER_1"}, {"speaker": "SPEAKER_2"}],
            [{"speaker": "SPEAKER_1"}, {"speaker": "SPEAKER_1"}],
        )

        self.assertFalse(matched)

    def test_run_reconciliation_diagnostic_reports_heavy_overlap(self) -> None:
        diagnostic = run_reconciliation_diagnostic("HeavyOverlap")

        self.assertEqual(diagnostic["case_id"], "HeavyOverlap")
        self.assertIn("reconciliation_pass", diagnostic)

    def test_build_diagnostic_receipt_row_marks_complete(self) -> None:
        row = build_diagnostic_receipt_row({"case_id": "HeavyOverlap", "reconciliation_pass": True})

        self.assertEqual(row["execution_status"], "reconciliation_diagnostic_complete")


if __name__ == "__main__":
    unittest.main()
