from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.demo_storyboard_review_pass_completion_summary import (
    COMPLETION_COLUMNS,
    build_completion_summary_row,
    write_outputs,
)
from src.demo_storyboard_review_pass_status import build_status_row


class DemoStoryboardReviewPassCompletionSummaryWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_status_and_completion_summary_artifacts(self) -> None:
        cards = [
            {"title": "Problem", "body": ""},
            {"title": "Pipeline", "body": ""},
        ]
        status_row = build_status_row(cards, {"Problem"})
        completion_row = build_completion_summary_row(status_row)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.demo_storyboard_review_pass_completion_summary.PROJECT_ROOT", root):
                paths = write_outputs(status_row, completion_row)

            self.assertEqual(len(paths), 6)
            for path in paths:
                self.assertTrue(path.exists())
            status_payload = json.loads(paths[1].read_text(encoding="utf-8"))
            self.assertEqual(status_payload["completed_count"], "1")
            with paths[3].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, COMPLETION_COLUMNS)
                self.assertEqual(list(reader)[0]["queue_status"], "queue_in_progress")
            self.assertIn(
                "Completion Summary",
                paths[5].read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
