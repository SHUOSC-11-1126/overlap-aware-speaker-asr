from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.llm_critic_review_pass import build_review_pass_receipt_rows, build_review_pass_row
from src.llm_critic_review_pass_next import (
    NEXT_COLUMNS,
    build_next_row,
    write_outputs,
)


class LlmCriticReviewPassNextWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_next_third_and_receipt_artifacts(self) -> None:
        queue_row = {"queue_order": "3", "case_id": "MidOverlap", "review_priority": "high"}
        pass_row = build_review_pass_row(
            queue_row,
            {
                "case_id": "MidOverlap",
                "label": "qualitative/demo",
                "risk_explanation": "mid overlap transcript",
                "candidate_repair": "review overlap boundaries",
                "uncertainty_note": "fixture",
            },
        )
        next_row = build_next_row(queue_row, pass_row, 2)
        receipt_rows = build_review_pass_receipt_rows(pass_row)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.llm_critic_review_pass_next.PROJECT_ROOT", root):
                outputs = write_outputs(next_row, pass_row, receipt_rows)

            for path in outputs:
                self.assertTrue(path.exists())

            next_csv, next_json, next_md, third_csv, third_json, third_md, receipt_json, receipt_md = outputs
            with next_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, NEXT_COLUMNS)
                self.assertEqual(list(reader)[0]["case_id"], "MidOverlap")
            self.assertEqual(json.loads(next_json.read_text(encoding="utf-8"))["completed_pass_count"], "2")
            self.assertIn("Review Pass Next", next_md.read_text(encoding="utf-8"))
            self.assertIn("LLM Critic Review Pass", third_md.read_text(encoding="utf-8"))
            self.assertIn("LLM Critic Review Receipt", receipt_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
