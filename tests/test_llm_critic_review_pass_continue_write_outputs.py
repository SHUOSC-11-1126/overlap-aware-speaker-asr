from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.llm_critic_review_pass import build_review_pass_receipt_rows, build_review_pass_row
from src.llm_critic_review_pass_continue import (
    CONTINUE_COLUMNS,
    build_continue_row,
    write_outputs,
)


class LlmCriticReviewPassContinueWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_continue_fourth_pass_and_receipt_artifacts(self) -> None:
        queue_row = {"case_id": "NoOverlap", "queue_order": "4", "review_priority": "medium"}
        pass_row = build_review_pass_row(queue_row, {"case_id": "NoOverlap", "label": "qualitative/demo"})
        continue_row = build_continue_row(queue_row, pass_row, completed_count=3)
        receipt_rows = build_review_pass_receipt_rows(pass_row)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.llm_critic_review_pass_continue.PROJECT_ROOT", root):
                outputs = write_outputs(continue_row, pass_row, receipt_rows)

            for path in outputs:
                self.assertTrue(path.exists())
            with outputs[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, CONTINUE_COLUMNS)
                self.assertEqual(list(reader)[0]["completed_pass_count"], "3")
            self.assertIn("LLM Critic Review Pass Continue", outputs[2].read_text(encoding="utf-8"))
            self.assertIn("LLM Critic Review Pass", outputs[5].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
