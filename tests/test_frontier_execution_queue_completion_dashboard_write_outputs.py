from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_queue_completion_dashboard import (
    DASHBOARD_COLUMNS,
    build_dashboard_row,
    write_outputs,
)


class FrontierExecutionQueueCompletionDashboardBuildRowTest(unittest.TestCase):
    def test_build_dashboard_row_returns_empty_when_inputs_missing(self) -> None:
        self.assertEqual(build_dashboard_row({}, {}), {})
        self.assertEqual(build_dashboard_row({"operator_frontier": "meeteval"}, {}), {})

    def test_build_dashboard_row_composes_operator_and_milestone_fields(self) -> None:
        row = build_dashboard_row(
            {"operator_frontier": "meeteval_compatibility"},
            {"next_milestone": "first_execution_queue_checkpoint_complete", "remaining_frontier_count": "4"},
        )
        self.assertEqual(row["current_first_frontier"], "meeteval_compatibility")
        self.assertEqual(row["next_milestone"], "first_execution_queue_checkpoint_complete")
        self.assertEqual(row["remaining_frontier_count"], "4")
        self.assertEqual(row["dominant_blocker"], "execution_receipt_fill_pending")
        self.assertIn("meeteval_compatibility", row["dashboard_note"])


class FrontierExecutionQueueCompletionDashboardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        row = build_dashboard_row(
            {"operator_frontier": "meeteval_compatibility"},
            {"next_milestone": "first_execution_queue_checkpoint_complete", "remaining_frontier_count": "4"},
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.frontier_execution_queue_completion_dashboard.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(row)

            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())

            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, DASHBOARD_COLUMNS)
                self.assertEqual(list(reader)[0]["current_first_frontier"], "meeteval_compatibility")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["dominant_blocker"], "execution_receipt_fill_pending")
            self.assertIn("Frontier Execution Queue Completion Dashboard", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
