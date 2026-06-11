from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.llm_critic_review_pass_completion_summary import (
    COMPLETION_COLUMNS,
    build_completion_summary_row,
    write_outputs,
)
from src.llm_critic_review_pass_status import build_status_rows


class LlmCriticReviewPassCompletionSummaryWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_status_and_completion_artifacts(self) -> None:
        queue_rows = [
            {"queue_order": "1", "case_id": "HeavyOverlap", "review_priority": "high"},
            {"queue_order": "2", "case_id": "NoOverlap", "review_priority": "medium"},
        ]
        status_rows = build_status_rows(queue_rows, {"HeavyOverlap"})
        completion_row = build_completion_summary_row(status_rows)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.llm_critic_review_pass_completion_summary.PROJECT_ROOT",
                root,
            ):
                outputs = write_outputs(status_rows, completion_row)

            for path in outputs:
                self.assertTrue(path.exists())

            status_csv, status_json, status_md, completion_csv, completion_json, completion_md = outputs
            with completion_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, COMPLETION_COLUMNS)
                self.assertEqual(list(reader)[0]["completed_count"], "1")
            payload = json.loads(completion_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["queue_status"], "queue_in_progress")
            self.assertIn("Completion Summary", completion_md.read_text(encoding="utf-8"))
            self.assertIn("LLM Critic Review Pass Status", status_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
