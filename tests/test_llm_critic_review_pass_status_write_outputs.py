from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.llm_critic_review_pass_status import (
    STATUS_COLUMNS,
    SUMMARY_COLUMNS,
    build_status_rows,
    build_summary_row,
    write_outputs,
)


class LlmCriticReviewPassStatusWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_status_and_summary_artifacts(self) -> None:
        queue_rows = [
            {"queue_order": "1", "case_id": "HeavyOverlap", "review_priority": "high"},
            {"queue_order": "2", "case_id": "NoOverlap", "review_priority": "medium"},
        ]
        status_rows = build_status_rows(queue_rows, {"HeavyOverlap"})
        summary_row = build_summary_row(status_rows)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.llm_critic_review_pass_status.PROJECT_ROOT", root):
                outputs = write_outputs(status_rows, summary_row)

            (
                status_csv,
                status_json,
                status_md,
                summary_csv,
                summary_json,
                summary_md,
            ) = outputs
            for path in outputs:
                self.assertTrue(path.exists())

            with status_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, STATUS_COLUMNS)
                loaded_status = list(reader)
            self.assertEqual(loaded_status[0]["pass_status"], "review_complete")
            self.assertEqual(loaded_status[1]["pass_status"], "pending_review")

            with summary_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SUMMARY_COLUMNS)
                self.assertEqual(list(reader)[0]["next_case_id"], "NoOverlap")

            self.assertEqual(json.loads(status_json.read_text(encoding="utf-8"))[1]["case_id"], "NoOverlap")
            self.assertEqual(json.loads(summary_json.read_text(encoding="utf-8"))["completed_count"], "1")
            self.assertIn("LLM Critic Review Pass Status", status_md.read_text(encoding="utf-8"))
            self.assertIn("LLM Critic Review Pass Status Summary", summary_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
