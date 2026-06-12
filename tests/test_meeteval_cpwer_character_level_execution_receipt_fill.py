from __future__ import annotations

import unittest
from unittest.mock import patch

from src.meeteval_cpwer_character_level_execution_receipt_fill import (
    build_fill_row,
    build_filled_receipt_rows,
    receipt_needs_character_fill,
)


class MeetEvalCharacterLevelExecutionReceiptFillTest(unittest.TestCase):
    def test_receipt_needs_character_fill_when_legacy_status_present(self) -> None:
        rows = [{"execution_status": "official_cpwer_narrow_dry_run_complete", "case_id": "NoOverlap"}]
        self.assertTrue(receipt_needs_character_fill(rows))

    def test_receipt_needs_character_fill_false_when_already_filled(self) -> None:
        rows = [{"execution_status": "character_level_cpwer_receipt_fill_complete", "case_id": "NoOverlap"}]
        self.assertFalse(receipt_needs_character_fill(rows))

    def test_build_filled_receipt_rows_uses_character_scores(self) -> None:
        character_rows = [
            {
                "case_id": "NoOverlap",
                "hypothesis_source": "separated_whisper",
                "execution_status": "character_level_cpwer_narrow_dry_run_complete",
                "official_cpwer": "0.053957",
                "official_cpwer_raw": "4.0",
                "cpwer_tool": "meeteval",
                "speaker_count": "2",
                "tokenization_mode": "character_spaced",
                "result_label": "experimental/frontier",
            }
        ]
        receipt_rows = build_filled_receipt_rows(character_rows, {"NoOverlap": "0.054312"})
        self.assertEqual(receipt_rows[0]["execution_status"], "character_level_cpwer_receipt_fill_complete")
        self.assertEqual(receipt_rows[0]["official_cpwer"], "0.053957")
        self.assertEqual(receipt_rows[0]["cpwer_bridge_lite"], "0.054312")

    def test_build_fill_row_marks_all_gold_scope(self) -> None:
        row = build_fill_row(5)
        self.assertEqual(row["fill_status"], "receipt_filled")
        self.assertEqual(row["case_count"], "5")
        self.assertEqual(row["execution_receipt_status"], "character_level_cpwer_receipt_fill_complete")

    def test_fill_character_level_receipt_requires_tokenization_complete(self) -> None:
        from src.meeteval_cpwer_character_level_execution_receipt_fill import fill_character_level_receipt

        with patch(
            "src.meeteval_cpwer_character_level_execution_receipt_fill.load_tokenization_summary",
            return_value={"queue_status": "queue_in_progress"},
        ):
            with self.assertRaises(RuntimeError):
                fill_character_level_receipt(force=True)


if __name__ == "__main__":
    unittest.main()
