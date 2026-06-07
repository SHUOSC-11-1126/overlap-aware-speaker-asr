from __future__ import annotations

import unittest
from collections import Counter

from src.meeteval_cpwer_alignment_drift_segment_granularity_diagnostic import (
    avg_duration,
    build_receipt_row,
    build_speaker_rows,
    build_summary_row,
    run_granularity_diagnostic,
)


class MeetEvalCpwerAlignmentDriftSegmentGranularityDiagnosticTest(unittest.TestCase):
    def test_avg_duration_handles_zero_count(self) -> None:
        self.assertEqual(avg_duration(0, 10.0), 0.0)

    def test_build_speaker_rows_report_delta(self) -> None:
        rows = build_speaker_rows(
            "HeavyOverlap",
            Counter({"SPEAKER_1": 10, "SPEAKER_2": 15}),
            Counter({"SPEAKER_1": 12, "SPEAKER_2": 13}),
            {"SPEAKER_1": 30.0, "SPEAKER_2": 45.0},
            {"SPEAKER_1": 48.0, "SPEAKER_2": 39.0},
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["granularity_match"], "False")

    def test_build_summary_row_counts_mismatches(self) -> None:
        summary = build_summary_row(
            "HeavyOverlap",
            [
                {
                    "case_id": "HeavyOverlap",
                    "speaker": "SPEAKER_1",
                    "reference_segment_count": "10",
                    "hypothesis_segment_count": "12",
                    "reference_avg_segment_duration_sec": "3.000",
                    "hypothesis_avg_segment_duration_sec": "3.500",
                    "avg_duration_delta_sec": "0.500",
                    "granularity_match": "False",
                }
            ],
        )

        self.assertEqual(summary["mismatched_speaker_count"], "1")

    def test_run_granularity_diagnostic_reports_heavy_overlap(self) -> None:
        speaker_rows, summary = run_granularity_diagnostic("HeavyOverlap")

        self.assertTrue(speaker_rows)
        self.assertEqual(summary["case_id"], "HeavyOverlap")

    def test_build_receipt_row_marks_complete(self) -> None:
        row = build_receipt_row({"case_id": "HeavyOverlap", "mismatched_speaker_count": "2"})

        self.assertEqual(row["execution_status"], "granularity_diagnostic_complete")


if __name__ == "__main__":
    unittest.main()
