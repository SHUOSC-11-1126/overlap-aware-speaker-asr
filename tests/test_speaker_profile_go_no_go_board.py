from __future__ import annotations

import unittest

from src.speaker_profile_go_no_go_board import build_summary_row, classify_go_no_go_state


class SpeakerProfileGoNoGoBoardTest(unittest.TestCase):
    def test_classify_go_no_go_state_marks_narrow_embedding_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("advance_to_narrow_embedding_baseline"), "go")

    def test_classify_go_no_go_state_marks_missing_as_no_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("signals_missing"), "no_go")

    def test_build_summary_row_marks_narrow_execution_ready(self) -> None:
        rows = [
            {"case_scope": "NoOverlap", "go_no_go_state": "go"},
            {"case_scope": "NoOverlap", "go_no_go_state": "go"},
            {"case_scope": "NoOverlap", "go_no_go_state": "go"},
            {"case_scope": "NoOverlap", "go_no_go_state": "go"},
        ]

        row = build_summary_row(
            rows,
            coordination_completion_flags={
                "oppositeoverlap": False,
                "heavyoverlap": False,
                "midoverlap": False,
                "lightoverlap": False,
                "case_scope": False,
            },
        )

        self.assertEqual(row["overall_state"], "narrow_execution_ready")
        self.assertEqual(row["primary_boundary"], "attribution_claims_still_blocked_by_weak_support")

    def test_build_summary_row_marks_oppositeoverlap_complete(self) -> None:
        rows = [
            {"case_scope": "NoOverlap", "go_no_go_state": "go"},
            {"case_scope": "NoOverlap", "go_no_go_state": "go"},
        ]

        row = build_summary_row(
            rows,
            coordination_completion_flags={
                "oppositeoverlap": True,
                "heavyoverlap": True,
                "midoverlap": True,
                "lightoverlap": True,
                "case_scope": True,
            },
        )

        self.assertEqual(row["overall_state"], "speaker_profile_oppositeoverlap_diagnostic_coordination_complete")

    def test_build_summary_row_marks_execution_not_ready(self) -> None:
        rows = [
            {"case_scope": "NoOverlap", "go_no_go_state": "no_go"},
        ]

        row = build_summary_row(rows)

        self.assertEqual(row["overall_state"], "execution_not_ready")


if __name__ == "__main__":
    unittest.main()
