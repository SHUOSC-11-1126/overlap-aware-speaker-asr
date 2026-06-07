from __future__ import annotations

import unittest

from src.meeteval_cpwer_alignment_drift_handoff import build_handoff_row, build_handoff_receipt_rows


class MeetEvalCpwerAlignmentDriftHandoffTest(unittest.TestCase):
    def test_build_handoff_row_documents_heavy_overlap(self) -> None:
        row = build_handoff_row(
            {
                "case_id": "HeavyOverlap",
                "alignment_gap": "0.016292",
                "drift_severity": "moderate",
            }
        )

        self.assertEqual(row["handoff_status"], "drift_handoff_ready")
        self.assertIn("HeavyOverlap", row["handoff_goal"])

    def test_build_handoff_receipt_rows_mark_documented(self) -> None:
        rows = build_handoff_receipt_rows({"case_id": "HeavyOverlap"})

        self.assertEqual(rows[0]["execution_status"], "handoff_documented")


if __name__ == "__main__":
    unittest.main()
