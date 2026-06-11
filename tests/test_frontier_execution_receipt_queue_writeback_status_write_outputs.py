from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_receipt_queue_writeback_status import (
    WRITEBACK_STATUS_COLUMNS,
    build_status_summary,
    build_writeback_status_rows,
    write_outputs,
)


class FrontierExecutionReceiptQueueWritebackStatusWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_summary_and_markdown(self) -> None:
        handoff_rows = [
            {
                "handoff_order": "1",
                "frontier_name": "meeteval_compatibility",
                "readiness_status": "receipt_ready_to_fill",
                "expected_outputs": "results/tables/meeteval_cpwer_execution_receipt.json",
            }
        ]

        with patch(
            "src.frontier_execution_receipt_queue_writeback_status.load_receipt_execution_status",
            return_value="template_only",
        ):
            rows = build_writeback_status_rows(handoff_rows)
        summary = build_status_summary(rows)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_execution_receipt_queue_writeback_status.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, summary_path, md_path = write_outputs(rows, summary)

            for path in (csv_path, json_path, summary_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, WRITEBACK_STATUS_COLUMNS)
                self.assertEqual(list(reader)[0]["writeback_status"], "awaiting_writeback")
            summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary_payload["combined_writeback_status"], "writeback_queue_ready")
            self.assertIn("Writeback Status", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
