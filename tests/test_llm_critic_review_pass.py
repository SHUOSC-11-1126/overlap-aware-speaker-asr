from __future__ import annotations

import unittest

from src.llm_critic_review_pass import (
    build_review_pass_lines,
    build_review_pass_receipt_lines,
    build_review_pass_receipt_rows,
    build_review_pass_row,
)


class LlmCriticReviewPassTest(unittest.TestCase):
    def test_build_review_pass_row_records_qualitative_outcome(self) -> None:
        row = build_review_pass_row(
            {"case_id": "HeavyOverlap", "review_priority": "high"},
            {
                "label": "qualitative/demo",
                "risk_explanation": "Medium risk state.",
                "candidate_repair": "Try cleaned transcript.",
                "uncertainty_note": "Attribution remains uncertain.",
            },
        )

        self.assertEqual(row["case_id"], "HeavyOverlap")
        self.assertIn("no verified transcript repair", row["review_outcome"].lower())

    def test_build_review_pass_lines_render_note(self) -> None:
        lines = build_review_pass_lines(
            {
                "case_id": "HeavyOverlap",
                "label": "qualitative/demo",
                "review_priority": "high",
                "risk_explanation": "Medium risk state.",
                "candidate_repair": "Try cleaned transcript.",
                "uncertainty_note": "Attribution remains uncertain.",
                "review_outcome": "Qualitative critic pass recorded for HeavyOverlap; no verified transcript repair was applied.",
            }
        )
        rendered = "\n".join(lines)

        self.assertIn("# LLM Critic Review Pass", rendered)
        self.assertIn("HeavyOverlap", rendered)

    def test_build_review_pass_receipt_rows_mark_review_complete(self) -> None:
        rows = build_review_pass_receipt_rows(
            {
                "case_id": "HeavyOverlap",
                "review_outcome": "Qualitative critic pass recorded for HeavyOverlap; no verified transcript repair was applied.",
            }
        )

        self.assertEqual(rows[0]["execution_status"], "review_complete")
        self.assertIn("no verified repair", rows[0]["writeback_note"].lower())

    def test_build_review_pass_receipt_lines_render_receipt(self) -> None:
        lines = build_review_pass_receipt_lines(
            [
                {
                    "execution_status": "review_complete",
                    "review_scope": "single_verified_case",
                    "case_id": "HeavyOverlap",
                    "review_outcome": "Qualitative critic pass recorded for HeavyOverlap; no verified transcript repair was applied.",
                    "expected_inputs": "Critic review queue head plus qualitative summary row.",
                    "writeback_note": "Qualitative critic pass complete; no verified repair claim was made.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("review_complete", rendered)


if __name__ == "__main__":
    unittest.main()
