from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_receipt_fill_queue_status import (
    FILL_STATUS_COLUMNS,
    build_fill_status_rows,
    build_status_summary,
    write_outputs,
)


class FrontierExecutionReceiptFillQueueStatusWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_summary_and_markdown(self) -> None:
        handoff_rows = [
            {
                "handoff_order": "1",
                "frontier_name": "meeteval_compatibility",
                "readiness_status": "receipt_ready_to_fill",
                "expected_outputs": "results/tables/meeteval_cpwer_execution_receipt.json",
            }
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_execution_receipt_fill_queue_status.load_receipt_execution_status",
                return_value="template_only",
            ), patch(
                "src.frontier_execution_receipt_fill_queue_status.PROJECT_ROOT",
                root,
            ):
                rows = build_fill_status_rows(handoff_rows)
                summary = build_status_summary(rows)
                csv_path, json_path, summary_path, md_path = write_outputs(rows, summary)

            self.assertEqual(len((csv_path, json_path, summary_path, md_path)), 4)
            for path in (csv_path, json_path, summary_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, FILL_STATUS_COLUMNS)
                self.assertEqual(list(reader)[0]["fill_status"], "awaiting_fill")
            summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary_payload["combined_fill_status"], "fill_queue_ready")
            self.assertIn("Fill Queue Status", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
