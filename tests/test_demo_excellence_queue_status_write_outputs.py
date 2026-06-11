from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.demo_excellence_queue_status import STATUS_COLUMNS, build_status_row, write_outputs


class DemoExcellenceQueueStatusWriteOutputsTest(unittest.TestCase):
    def test_build_status_row_marks_combined_complete_when_both_queues_complete(self) -> None:
        row = build_status_row(
            {"queue_status": "queue_complete"},
            {"queue_status": "queue_complete"},
        )
        self.assertEqual(row["combined_queue_status"], "queue_complete")

    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        status_row = build_status_row(
            {"queue_status": "queue_in_progress"},
            {"queue_status": "queue_complete"},
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.demo_excellence_queue_status.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(status_row)

            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())

            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, STATUS_COLUMNS)
                self.assertEqual(list(reader)[0]["combined_queue_status"], "queue_in_progress")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["scope"], "demo_excellence_review_queues")
            self.assertIn("Demo Excellence Queue Status", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
