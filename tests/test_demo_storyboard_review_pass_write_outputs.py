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
    write_outputs,
)


class DemoStoryboardReviewPassWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_review_and_receipt_artifacts(self) -> None:
        review_row = build_review_row({"title": "Problem", "body": "Overlap-aware ASR challenge."})
        receipt_rows = build_review_receipt_rows(review_row, card_count=6)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.demo_storyboard_review_pass.PROJECT_ROOT", root):
                paths = write_outputs(review_row, receipt_rows)

            for path in paths:
                self.assertTrue(path.exists())
            with paths[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, REVIEW_COLUMNS)
                self.assertEqual(list(reader)[0]["review_status"], "review_complete")
            payload = json.loads(paths[1].read_text(encoding="utf-8"))
            self.assertEqual(payload["card_title"], "Problem")
            self.assertIn("Storyboard Review Pass", paths[2].read_text(encoding="utf-8"))
            receipt_payload = json.loads(paths[3].read_text(encoding="utf-8"))
            self.assertEqual(receipt_payload[0]["execution_status"], "review_complete")


if __name__ == "__main__":
    unittest.main()
