from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_receipt_fill_execution_handoff import (
    HANDOFF_COLUMNS,
    build_handoff_rows,
    write_outputs,
)


class FrontierExecutionReceiptFillExecutionHandoffWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        rows = build_handoff_rows(
            {
                "meeteval_fill_execution_status": "awaiting_fill",
                "speaker_profile_fill_execution_status": "fill_complete",
                "external_staging_fill_execution_status": "receipt_missing",
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_execution_receipt_fill_execution_handoff.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(rows)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, HANDOFF_COLUMNS)
                parsed = list(reader)
                self.assertEqual(parsed[0]["frontier_name"], "meeteval_compatibility")
                self.assertEqual(parsed[0]["fill_execution_status"], "awaiting_fill")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload), 3)
            self.assertIn("Fill Execution Handoff", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
