from __future__ import annotations

import unittest

from src.meeteval_cpwer_alignment_drift_diagnostic import (
    build_drift_diagnostic_receipt_rows,
    build_drift_diagnostic_row,
    classify_drift_severity,
    select_drift_rows,
)


class MeetEvalCpwerAlignmentDriftDiagnosticTest(unittest.TestCase):
    def test_select_drift_rows_filters_matched_cases(self) -> None:
        rows = select_drift_rows(
            [
                {"alignment_status": "matched", "case_id": "NoOverlap"},
                {"alignment_status": "drift", "case_id": "HeavyOverlap"},
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["case_id"], "HeavyOverlap")

    def test_classify_drift_severity_marks_moderate_gap(self) -> None:
        self.assertEqual(classify_drift_severity(0.016292), "moderate")

    def test_build_drift_diagnostic_row_documents_heavy_overlap(self) -> None:
        row = build_drift_diagnostic_row(
            {
                "case_id": "HeavyOverlap",
                "hypothesis_source": "separated_whisper_cleaned",
                "cpwer_bridge_lite": 0.162827,
                "speaker_macro_cer": 0.146535,
                "alignment_gap": 0.016292,
            }
        )

        self.assertEqual(row["diagnostic_status"], "drift_documented")
        self.assertIn("HeavyOverlap", row["likely_cause"])

    def test_build_drift_diagnostic_receipt_rows_mark_complete(self) -> None:
        rows = build_drift_diagnostic_receipt_rows([{"case_id": "HeavyOverlap"}])

        self.assertEqual(rows[0]["execution_status"], "diagnostic_complete")
        self.assertEqual(rows[0]["drift_case_count"], "1")


if __name__ == "__main__":
    unittest.main()
