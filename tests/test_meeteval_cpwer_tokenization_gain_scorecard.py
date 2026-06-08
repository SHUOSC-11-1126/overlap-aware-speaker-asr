from __future__ import annotations

import unittest

from src.meeteval_cpwer_tokenization_gain_scorecard import (
    build_scorecard_rows,
    build_summary_row,
    compute_gain,
)


class MeetEvalCpwerTokenizationGainScorecardTest(unittest.TestCase):
    def test_compute_gain(self) -> None:
        self.assertEqual(compute_gain("4.0", "0.053957"), "3.946043")

    def test_build_scorecard_rows_marks_adapted_and_aligned(self) -> None:
        raw_rows = [{"case_id": "NoOverlap", "official_cpwer": "4.0"}]
        char_rows = [{"case_id": "NoOverlap", "official_cpwer": "0.053957"}]
        bridge = {"NoOverlap": "0.054312"}

        rows = build_scorecard_rows(raw_rows, char_rows, bridge)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["adaptation_status"], "adapted_and_aligned")
        self.assertEqual(rows[0]["raw_to_character_gain"], "3.946043")

    def test_build_summary_row_recommends_character_spaced_when_all_cases_align(self) -> None:
        rows = [
            {
                "case_id": "NoOverlap",
                "raw_to_character_gain": "3.9",
                "adaptation_status": "adapted_and_aligned",
            },
            {
                "case_id": "LightOverlap",
                "raw_to_character_gain": "3.8",
                "adaptation_status": "adapted_and_aligned",
            },
        ]

        summary = build_summary_row(rows)

        self.assertEqual(summary["recommended_default_mode"], "character_spaced")
        self.assertEqual(summary["adapted_and_aligned_count"], "2")
        self.assertEqual(summary["max_gain_case"], "NoOverlap")

    def test_build_summary_row_falls_back_to_review_when_not_all_cases_align(self) -> None:
        rows = [
            {
                "case_id": "NoOverlap",
                "raw_to_character_gain": "3.9",
                "adaptation_status": "adapted_and_aligned",
            },
            {
                "case_id": "HeavyOverlap",
                "raw_to_character_gain": "0.0",
                "adaptation_status": "adapted_but_residual_drift",
            },
        ]

        summary = build_summary_row(rows)

        self.assertEqual(summary["recommended_default_mode"], "case_by_case_review")


if __name__ == "__main__":
    unittest.main()
