from __future__ import annotations

import unittest

from src.meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_handoff import (
    build_handoff_receipt_rows,
    build_handoff_row,
)


class MeetEvalCpwerAlignmentDriftSegmentRedistributionDiagnosticHandoffTest(unittest.TestCase):
    def test_build_handoff_row_targets_cpwer_bridge(self) -> None:
        row = build_handoff_row(
            {
                "case_id": "HeavyOverlap",
                "redistribution_mismatch_count": "2",
                "dominant_blocker": "SPEAKER_1 hypothesis_merged",
            }
        )

        self.assertEqual(row["case_id"], "HeavyOverlap")
        self.assertIn("cpwer_bridge", row["cpwer_bridge_target"])

    def test_build_handoff_receipt_rows_document_handoff(self) -> None:
        rows = build_handoff_receipt_rows({"case_id": "HeavyOverlap"})

        self.assertEqual(rows[0]["execution_status"], "handoff_documented")


if __name__ == "__main__":
    unittest.main()
