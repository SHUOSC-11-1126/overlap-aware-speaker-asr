from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.llm_critic_review_pass import (
    PASS_COLUMNS,
    RECEIPT_COLUMNS,
    build_review_pass_receipt_rows,
    build_review_pass_row,
    write_outputs,
)


class LlmCriticReviewPassWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_pass_and_receipt_artifacts(self) -> None:
        queue_row = {"case_id": "HeavyOverlap", "review_priority": "high", "candidate_repair": "trim overlap"}
        qualitative_row = {
            "case_id": "HeavyOverlap",
            "label": "qualitative/demo",
            "risk_explanation": "overlap-heavy transcript",
            "candidate_repair": "trim overlap",
            "uncertainty_note": "fixture",
        }
        pass_row = build_review_pass_row(queue_row, qualitative_row)
        receipt_rows = build_review_pass_receipt_rows(pass_row)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.llm_critic_review_pass.PROJECT_ROOT", root):
                outputs = write_outputs(pass_row, receipt_rows)

            pass_csv, pass_json, pass_md, receipt_json, receipt_md = outputs
            for path in outputs:
                self.assertTrue(path.exists())

            with pass_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, PASS_COLUMNS)
                self.assertEqual(list(reader)[0]["case_id"], "HeavyOverlap")

            self.assertEqual(json.loads(pass_json.read_text(encoding="utf-8"))["review_priority"], "high")
            self.assertIn("LLM Critic Review Pass", pass_md.read_text(encoding="utf-8"))

            receipt_payload = json.loads(receipt_json.read_text(encoding="utf-8"))
            self.assertEqual(receipt_payload[0]["execution_status"], "review_complete")
            self.assertEqual(receipt_payload[0].keys(), set(RECEIPT_COLUMNS))
            self.assertIn("LLM Critic Review Receipt", receipt_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
