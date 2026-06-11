from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_queue_receipt_open_card import (
    RECEIPT_OPEN_COLUMNS,
    build_receipt_open_card_row,
    write_outputs,
)


class FrontierExecutionQueueReceiptOpenCardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        row = build_receipt_open_card_row(
            [
                {
                    "frontier_name": "meeteval_compatibility",
                    "chain_status": "execution_chain_ready",
                    "receipt_target": "results/tables/meeteval_cpwer_execution_receipt.json",
                }
            ]
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.frontier_execution_queue_receipt_open_card.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(row)

            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())

            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, RECEIPT_OPEN_COLUMNS)
                self.assertEqual(list(reader)[0]["frontier_name"], "meeteval_compatibility")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["chain_status"], "execution_chain_ready")
            self.assertIn("Frontier Execution Queue Receipt Open Card", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
