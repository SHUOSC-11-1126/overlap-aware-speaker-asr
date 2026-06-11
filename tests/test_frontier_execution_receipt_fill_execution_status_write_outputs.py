from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_receipt_fill_execution_status import (
    STATUS_COLUMNS,
    write_outputs,
)


class FrontierExecutionReceiptFillExecutionStatusWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_status_csv_json_and_markdown(self) -> None:
        status_row = {
            "scope": "frontier_execution_receipt_fill_execution",
            "meeteval_fill_execution_status": "awaiting_fill",
            "speaker_profile_fill_execution_status": "fill_complete",
            "external_staging_fill_execution_status": "awaiting_fill",
            "combined_fill_execution_status": "fill_execution_in_progress",
            "status_note": "Template-only receipts remain unfilled.",
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_execution_receipt_fill_execution_status.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(status_row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, STATUS_COLUMNS)
                self.assertEqual(list(reader)[0]["combined_fill_execution_status"], "fill_execution_in_progress")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["meeteval_fill_execution_status"], "awaiting_fill")
            self.assertIn("Fill Execution Status", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
