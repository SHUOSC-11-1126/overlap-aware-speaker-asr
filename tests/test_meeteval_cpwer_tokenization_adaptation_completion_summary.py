from __future__ import annotations

import unittest

from src.meeteval_cpwer_tokenization_adaptation_completion_summary import (
    build_completion_lines,
    build_completion_row,
)


class MeetEvalCpwerTokenizationAdaptationCompletionSummaryTest(unittest.TestCase):
    def test_build_completion_row_marks_queue_complete_when_all_aligned(self) -> None:
        row = build_completion_row(
            [
                {"reconciliation_status": "aligned"},
                {"reconciliation_status": "aligned"},
            ],
            [
                {"root_cause": "no_whitespace_word_tokenization"},
            ],
        )
        self.assertEqual(row["queue_status"], "queue_complete")
        self.assertEqual(row["aligned_count"], "2")
        self.assertEqual(row["tokenization_root_cause_count"], "1")

    def test_build_completion_row_marks_in_progress_with_drift(self) -> None:
        row = build_completion_row(
            [{"reconciliation_status": "minor_drift"}],
            [],
        )
        self.assertEqual(row["queue_status"], "queue_in_progress")

    def test_build_completion_lines_renders_markdown_table(self) -> None:
        row = build_completion_row(
            [{"reconciliation_status": "aligned"}],
            [],
        )
        lines = build_completion_lines(row)
        self.assertIn("# MeetEval cpWER Tokenization Adaptation Completion Summary", lines[0])
        self.assertTrue(any("meeteval_cpwer_tokenization_adaptation" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
