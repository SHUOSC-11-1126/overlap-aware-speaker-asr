from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.demo_walkthrough_review_pass import build_review_receipt_rows, build_review_row
from src.demo_walkthrough_review_pass_continue import (
    CONTINUE_COLUMNS,
    build_continue_row,
    write_outputs,
)


class DemoWalkthroughReviewPassContinueWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_continue_third_review_and_receipt_artifacts(self) -> None:
        next_step = {"step_id": "3", "focus": "Routing takeaway"}
        review_row = build_review_row(next_step)
        continue_row = build_continue_row(next_step, 2)
        receipt_rows = build_review_receipt_rows(review_row, step_count=5)
        for receipt in receipt_rows:
            receipt["review_scope"] = "third_walkthrough_step"

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.demo_walkthrough_review_pass_continue.PROJECT_ROOT", root):
                paths = write_outputs(continue_row, review_row, receipt_rows)

            self.assertEqual(len(paths), 8)
            for path in paths:
                self.assertTrue(path.exists())
            with paths[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, CONTINUE_COLUMNS)
                self.assertEqual(list(reader)[0]["step_id"], "3")
            continue_payload = json.loads(paths[1].read_text(encoding="utf-8"))
            self.assertEqual(continue_payload["review_order"], "3")
            self.assertIn("Review Pass Continue", paths[2].read_text(encoding="utf-8"))
            third_payload = json.loads(paths[4].read_text(encoding="utf-8"))
            self.assertEqual(third_payload["review_order"], "3")
            receipt_payload = json.loads(paths[6].read_text(encoding="utf-8"))
            self.assertEqual(receipt_payload[0]["execution_status"], "review_complete")


if __name__ == "__main__":
    unittest.main()
