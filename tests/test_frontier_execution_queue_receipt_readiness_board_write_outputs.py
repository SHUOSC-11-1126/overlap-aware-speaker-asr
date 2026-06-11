from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_queue_receipt_readiness_board import (
    READINESS_COLUMNS,
    build_readiness_rows,
    write_outputs,
)


class FrontierExecutionQueueReceiptReadinessBoardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        rows = build_readiness_rows(
            [
                {
                    "frontier_name": "demo_excellence",
                    "chain_status": "execution_chain_ready",
                    "expected_outputs": "results/tables/demo_walkthrough_receipt.json",
                }
            ]
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.frontier_execution_queue_receipt_readiness_board.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(rows)

            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, READINESS_COLUMNS)
                self.assertEqual(list(reader)[0]["readiness_state"], "ready_for_receipt_fill")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["frontier_name"], "demo_excellence")
            self.assertIn("Frontier Execution Queue Receipt Readiness Board", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
