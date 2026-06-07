from __future__ import annotations

import unittest

from src.meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic import (
    build_receipt_row,
    build_speaker_rows,
    build_summary_row,
    classify_redistribution,
    run_redistribution_diagnostic,
)


class MeetEvalCpwerAlignmentDriftSegmentRedistributionDiagnosticTest(unittest.TestCase):
    def test_classify_redistribution(self) -> None:
        self.assertEqual(classify_redistribution(-1), "hypothesis_merged")
        self.assertEqual(classify_redistribution(1), "hypothesis_split")
        self.assertEqual(classify_redistribution(0), "matched")

    def test_build_speaker_rows_report_pattern(self) -> None:
        rows = build_speaker_rows(
            "HeavyOverlap",
            [
                {
                    "case_id": "HeavyOverlap",
                    "speaker": "SPEAKER_1",
                    "reference_segment_count": "11",
                    "hypothesis_segment_count": "10",
                },
                {
                    "case_id": "HeavyOverlap",
                    "speaker": "SPEAKER_2",
                    "reference_segment_count": "14",
                    "hypothesis_segment_count": "15",
                },
            ],
        )

        self.assertEqual(rows[0]["redistribution_pattern"], "hypothesis_merged")
        self.assertEqual(rows[1]["redistribution_pattern"], "hypothesis_split")

    def test_build_summary_row_counts_mismatches(self) -> None:
        summary = build_summary_row(
            "HeavyOverlap",
            [
                {
                    "case_id": "HeavyOverlap",
                    "speaker": "SPEAKER_1",
                    "reference_segment_count": "11",
                    "hypothesis_segment_count": "10",
                    "segment_count_delta": "-1",
                    "redistribution_pattern": "hypothesis_merged",
                    "pattern_match": "False",
                }
            ],
        )

        self.assertEqual(summary["redistribution_mismatch_count"], "1")

    def test_run_redistribution_diagnostic_reports_heavy_overlap(self) -> None:
        speaker_rows, summary = run_redistribution_diagnostic("HeavyOverlap")

        self.assertTrue(speaker_rows)
        self.assertEqual(summary["case_id"], "HeavyOverlap")

    def test_build_receipt_row_marks_complete(self) -> None:
        row = build_receipt_row({"case_id": "HeavyOverlap", "redistribution_mismatch_count": "2"})

        self.assertEqual(row["execution_status"], "redistribution_diagnostic_complete")


if __name__ == "__main__":
    unittest.main()
