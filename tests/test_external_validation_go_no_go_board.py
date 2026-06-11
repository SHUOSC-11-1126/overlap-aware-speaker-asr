from __future__ import annotations

import unittest

from src.external_validation_go_no_go_board import build_summary_row, classify_go_no_go_state


class ExternalValidationGoNoGoBoardTest(unittest.TestCase):
    def test_classify_go_no_go_state_marks_pending_as_no_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("pending_confirmation"), "no_go")

    def test_classify_go_no_go_state_marks_ready_as_go(self) -> None:
        self.assertEqual(classify_go_no_go_state("ready_for_staging_review"), "go")

    def test_build_summary_row_marks_license_blocker(self) -> None:
        rows = [
            {
                "dataset_name": "AISHELL-4",
                "go_no_go_state": "no_go",
                "blocker": "license_confirmation_pending",
            },
            {
                "dataset_name": "AISHELL-4",
                "go_no_go_state": "no_go",
                "blocker": "blocked_by_license_gate",
            },
        ]

        row = build_summary_row(rows)

        self.assertEqual(row["overall_state"], "blocked_by_license_confirmation")
        self.assertEqual(row["no_go_count"], "2")

    def test_build_summary_row_after_license_unblock(self) -> None:
        rows = [
            {
                "dataset_name": "AISHELL-4",
                "go_no_go_state": "go",
                "blocker": "none_documented",
            },
            {
                "dataset_name": "AISHELL-4",
                "go_no_go_state": "go",
                "blocker": "none_documented",
            },
            {
                "dataset_name": "AISHELL-4",
                "go_no_go_state": "go",
                "blocker": "audio_staging_pending",
            },
        ]
        row = build_summary_row(rows)
        self.assertEqual(row["overall_state"], "ready_for_optional_audio_staging")
        self.assertEqual(row["primary_blocker"], "audio_staging_pending")


if __name__ == "__main__":
    unittest.main()
