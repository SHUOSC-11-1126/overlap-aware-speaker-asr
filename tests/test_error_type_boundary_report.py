from __future__ import annotations

import unittest

from src.error_type_boundary_report import build_boundary_rows, build_summary_rows


class ErrorTypeBoundaryReportTest(unittest.TestCase):
    def test_build_boundary_rows_flags_insertion_harm(self) -> None:
        error_rows = [
            {
                "case_id": "LightOverlap",
                "method": "separated_whisper",
                "dominant_error_type": "insertion",
                "insertion_count": "54",
                "repetition_count": "38",
                "removed_count_if_cleaned": "0",
            },
            {
                "case_id": "NoOverlap",
                "method": "separated_whisper",
                "dominant_error_type": "substitution",
                "insertion_count": "1",
                "repetition_count": "3",
                "removed_count_if_cleaned": "0",
            },
        ]
        cer_by_case = {
            "LightOverlap": {"mixed_whisper": 0.21, "separated_whisper": 0.48},
            "NoOverlap": {"mixed_whisper": 0.22, "separated_whisper": 0.05},
        }
        rows = build_boundary_rows(error_rows, cer_by_case)
        by_id = {row["case_id"]: row for row in rows}
        self.assertTrue(by_id["LightOverlap"]["explains_separation_harm"])
        self.assertFalse(by_id["NoOverlap"]["explains_separation_harm"])

    def test_build_summary_rows_counts_harmful_cases(self) -> None:
        rows = [
            {"separation_helps": False, "explains_separation_harm": True, "repetition_count": 38},
            {"separation_helps": True, "explains_separation_harm": False, "repetition_count": 3},
        ]
        summary = build_summary_rows(rows)
        metrics = {row["metric"]: row["value"] for row in summary}
        self.assertEqual(metrics["separation_harmful_cases"], "1")
        self.assertEqual(metrics["harmful_cases_insertion_explained"], "1")


if __name__ == "__main__":
    unittest.main()
