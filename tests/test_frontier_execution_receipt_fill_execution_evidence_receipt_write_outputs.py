from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_receipt_fill_execution_evidence_receipt import (
    EVIDENCE_RECEIPT_COLUMNS,
    build_evidence_receipt_row,
    write_outputs,
)


class FrontierExecutionReceiptFillExecutionEvidenceReceiptWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        row = build_evidence_receipt_row(
            {
                "operator_frontier": "meeteval_compatibility",
                "operator_action": "fill_execution_receipt",
                "operator_evidence": "results/tables/meeteval_cpwer_execution_status.json",
                "operator_receipt": "results/tables/meeteval_cpwer_execution_status.json",
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_execution_receipt_fill_execution_evidence_receipt.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, EVIDENCE_RECEIPT_COLUMNS)
                self.assertEqual(list(reader)[0]["receipt_frontier"], "meeteval_compatibility")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("template_only", payload["receipt_completion_signal"])
            self.assertIn("Evidence Receipt", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
