from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.llm_critic_review_pass import build_review_pass_receipt_rows, build_review_pass_row
from src.llm_critic_review_pass_advance import (
    ADVANCE_COLUMNS,
    build_advance_row,
    write_outputs,
)


class LlmCriticReviewPassAdvanceWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_advance_second_pass_and_receipt_artifacts(self) -> None:
        queue_row = {"case_id": "LightOverlap", "queue_order": "2", "review_priority": "high"}
        qualitative_row = {"case_id": "LightOverlap", "label": "qualitative/demo", "risk_explanation": "fixture"}
        pass_row = build_review_pass_row(queue_row, qualitative_row)
        advance_row = build_advance_row(queue_row, pass_row, "HeavyOverlap")
        receipt_rows = build_review_pass_receipt_rows(pass_row)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.llm_critic_review_pass_advance.PROJECT_ROOT", root):
                outputs = write_outputs(advance_row, pass_row, receipt_rows)

            for path in outputs:
                self.assertTrue(path.exists(), msg=str(path))

            advance_csv = outputs[0]
            with advance_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, ADVANCE_COLUMNS)
                self.assertEqual(list(reader)[0]["case_id"], "LightOverlap")

            self.assertEqual(json.loads(outputs[1].read_text(encoding="utf-8"))["prior_pass_status"], advance_row["prior_pass_status"])
            self.assertIn("LLM Critic Review Pass Advance", outputs[2].read_text(encoding="utf-8"))
            self.assertIn("LLM Critic Review Pass", outputs[5].read_text(encoding="utf-8"))
            self.assertIn("LLM Critic Review Receipt", outputs[7].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
