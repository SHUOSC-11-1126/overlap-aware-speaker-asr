from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.demo_storyboard_review_pass import (
    REVIEW_COLUMNS,
    build_review_receipt_rows,
    build_review_row,
)
from src.demo_storyboard_review_pass_second_continue import (
    CONTINUE_COLUMNS,
    build_continue_row,
    write_outputs,
)


class DemoStoryboardReviewPassSecondContinueWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_second_continue_fourth_review_and_receipt_artifacts(self) -> None:
        next_card = {"title": "Frontier", "body": "Research frontier."}
        review_row = build_review_row(next_card, card_index=4)
        continue_row = build_continue_row(next_card, 4, 3)
        receipt_rows = build_review_receipt_rows(review_row, card_count=6)
        for receipt in receipt_rows:
            receipt["execution_status"] = "review_complete"
            receipt["review_scope"] = "fourth_storyboard_card"

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.demo_storyboard_review_pass_second_continue.PROJECT_ROOT", root):
                paths = write_outputs(continue_row, review_row, receipt_rows)

            self.assertEqual(len(paths), 8)
            for path in paths:
                self.assertTrue(path.exists())
            with paths[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, CONTINUE_COLUMNS)
                self.assertEqual(list(reader)[0]["card_title"], "Frontier")
            continue_payload = json.loads(paths[1].read_text(encoding="utf-8"))
            self.assertEqual(continue_payload["review_order"], "4")
            self.assertIn("Second Continue", paths[2].read_text(encoding="utf-8"))
            with paths[3].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, REVIEW_COLUMNS)
                self.assertEqual(list(reader)[0]["review_order"], "4")
            receipt_payload = json.loads(paths[6].read_text(encoding="utf-8"))
            self.assertEqual(receipt_payload[0]["execution_status"], "review_complete")


if __name__ == "__main__":
    unittest.main()
