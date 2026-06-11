from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_receipt_queue_writeback_handoff import (
    HANDOFF_COLUMNS,
    build_handoff_rows,
    write_outputs,
)


class FrontierExecutionReceiptQueueWritebackHandoffWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        rows = build_handoff_rows(
            [
                {"frontier_name": "meeteval_compatibility", "writeback_status": "awaiting_writeback"},
                {"frontier_name": "speaker_profile", "writeback_status": "writeback_complete"},
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_execution_receipt_queue_writeback_handoff.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(rows)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, HANDOFF_COLUMNS)
                parsed = list(reader)
                self.assertEqual(len(parsed), 3)
                self.assertEqual(parsed[0]["frontier_name"], "meeteval_compatibility")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["writeback_status"], "awaiting_writeback")
            self.assertIn("Writeback Handoff", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
