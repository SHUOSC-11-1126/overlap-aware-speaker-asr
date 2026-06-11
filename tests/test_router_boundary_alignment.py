from __future__ import annotations

import unittest

from src.router_boundary_alignment import (
    build_alignment_rows,
    build_summary_rows,
    prefers_separation_route,
)


class RouterBoundaryAlignmentTest(unittest.TestCase):
    def test_prefers_separation_route(self) -> None:
        self.assertTrue(prefers_separation_route("separated_whisper"))
        self.assertTrue(prefers_separation_route("separated_whisper_cleaned"))
        self.assertFalse(prefers_separation_route("mixed_whisper"))

    def test_build_alignment_rows_marks_phase_alignment(self) -> None:
        cer_rows = [
            {"case_id": "NoOverlap", "method": "mixed_whisper", "cer": "0.22"},
            {"case_id": "NoOverlap", "method": "separated_whisper", "cer": "0.05"},
            {"case_id": "NoOverlap", "method": "separated_whisper_cleaned", "cer": "0.09"},
            {"case_id": "LightOverlap", "method": "mixed_whisper", "cer": "0.21"},
            {"case_id": "LightOverlap", "method": "separated_whisper", "cer": "0.48"},
            {"case_id": "LightOverlap", "method": "separated_whisper_cleaned", "cer": "0.38"},
        ]
        decision_rows = [
            {
                "case_id": "NoOverlap",
                "selected_method": "separated_whisper",
                "decision_rule": "overlap_level==0",
            },
            {
                "case_id": "LightOverlap",
                "selected_method": "mixed_whisper",
                "decision_rule": "overlap_level in [1,2]",
            },
        ]
        rows = build_alignment_rows(cer_rows, decision_rows)
        by_id = {row["case_id"]: row for row in rows}
        self.assertTrue(by_id["NoOverlap"]["router_aligns_with_phase"])
        self.assertTrue(by_id["LightOverlap"]["router_aligns_with_phase"])
        self.assertTrue(by_id["NoOverlap"]["router_matches_oracle"])
        self.assertTrue(by_id["LightOverlap"]["router_matches_oracle"])

    def test_build_summary_rows_reports_rates(self) -> None:
        rows = [
            {
                "router_matches_oracle": True,
                "router_aligns_with_phase": True,
                "router_regret_cer": 0.0,
            },
            {
                "router_matches_oracle": False,
                "router_aligns_with_phase": True,
                "router_regret_cer": 0.1,
            },
        ]
        summary = build_summary_rows(rows)
        metrics = {row["metric"]: row["value"] for row in summary}
        self.assertEqual(metrics["gold_case_count"], "2")
        self.assertEqual(metrics["router_oracle_match_rate"], "0.5")
        self.assertEqual(metrics["router_phase_alignment_rate"], "1.0")


if __name__ == "__main__":
    unittest.main()
