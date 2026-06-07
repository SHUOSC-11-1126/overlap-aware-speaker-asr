from __future__ import annotations

import unittest

from src.meeteval_cpwer_alignment import (
    build_alignment_row,
    build_alignment_summary_lines,
    build_alignment_summary_row,
)


class MeetEvalCpwerAlignmentTest(unittest.TestCase):
    def test_build_alignment_row_marks_matched_metrics(self) -> None:
        row = build_alignment_row(
            {
                "case_id": "NoOverlap",
                "hypothesis_source": "separated_whisper",
                "cpwer_bridge_lite": 0.054312,
            },
            speaker_macro_cer=0.054312,
        )

        self.assertEqual(row["alignment_status"], "matched")
        self.assertEqual(row["alignment_gap"], 0.0)

    def test_build_alignment_row_marks_drift(self) -> None:
        row = build_alignment_row(
            {
                "case_id": "LightOverlap",
                "hypothesis_source": "separated_whisper_cleaned",
                "cpwer_bridge_lite": 0.135164,
            },
            speaker_macro_cer=0.2,
        )

        self.assertEqual(row["alignment_status"], "drift")

    def test_build_alignment_summary_row_counts_matches(self) -> None:
        summary = build_alignment_summary_row(
            [
                {"alignment_gap": 0.0, "alignment_status": "matched"},
                {"alignment_gap": 0.01, "alignment_status": "drift"},
            ]
        )

        self.assertEqual(summary["matched_count"], 1)
        self.assertEqual(summary["average_alignment_gap"], 0.005)

    def test_build_alignment_summary_lines_render_summary(self) -> None:
        lines = build_alignment_summary_lines(
            {
                "scope": "all_gold_cases",
                "case_count": 5,
                "matched_count": 5,
                "average_alignment_gap": 0.0,
                "observation": "Cross-metric alignment audit.",
            }
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval cpWER Alignment Summary", rendered)
        self.assertIn("all_gold_cases", rendered)


if __name__ == "__main__":
    unittest.main()
