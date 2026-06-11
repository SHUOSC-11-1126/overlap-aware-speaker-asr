from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.demo_storyboard_review_pass_status import (
    STATUS_COLUMNS,
    build_status_row,
    write_outputs,
)


class DemoStoryboardReviewPassStatusWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_status_csv_json_and_markdown(self) -> None:
        cards = [
            {"title": "Problem", "body": ""},
            {"title": "Pipeline", "body": ""},
            {"title": "Findings", "body": ""},
        ]
        status_row = build_status_row(cards, {"Problem", "Pipeline"})

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.demo_storyboard_review_pass_status.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(status_row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, STATUS_COLUMNS)
                self.assertEqual(list(reader)[0]["queue_status"], "queue_in_progress")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["completed_count"], "2")
            self.assertIn("Review Pass Status", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
