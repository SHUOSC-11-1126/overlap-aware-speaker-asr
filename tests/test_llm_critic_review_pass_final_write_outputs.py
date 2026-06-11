from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.llm_critic_review_pass import build_review_pass_receipt_rows, build_review_pass_row
from src.llm_critic_review_pass_final import (
    FINAL_COLUMNS,
    build_final_row,
    write_outputs,
)


class LlmCriticReviewPassFinalWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_final_fifth_pass_and_receipt_artifacts(self) -> None:
        queue_row = {"case_id": "OppositeOverlap", "queue_order": "5", "review_priority": "high"}
        pass_row = build_review_pass_row(queue_row, {"case_id": "OppositeOverlap", "label": "qualitative/demo"})
        final_row = build_final_row(queue_row, pass_row, completed_count=4)
        receipt_rows = build_review_pass_receipt_rows(pass_row)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.llm_critic_review_pass_final.PROJECT_ROOT", root):
                outputs = write_outputs(final_row, pass_row, receipt_rows)

            for path in outputs:
                self.assertTrue(path.exists())
            with outputs[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, FINAL_COLUMNS)
                self.assertIn("gold review queue is now complete", list(reader)[0]["final_note"])
            self.assertIn("LLM Critic Review Pass Final", outputs[2].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
