from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_receipt_queue_completion_dashboard import (
    DASHBOARD_COLUMNS,
    build_dashboard_row,
    write_outputs,
)


class FrontierExecutionReceiptQueueCompletionDashboardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        row = build_dashboard_row(
            {"operator_frontier": "meeteval_compatibility"},
            {
                "next_milestone": "first_execution_receipt_filled",
                "remaining_frontier_count": "4",
            },
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_execution_receipt_queue_completion_dashboard.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, DASHBOARD_COLUMNS)
                self.assertEqual(list(reader)[0]["current_first_frontier"], "meeteval_compatibility")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["dominant_blocker"], "receipt_template_fill_pending")
            self.assertIn(
                "Receipt Queue Completion Dashboard",
                md_path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
