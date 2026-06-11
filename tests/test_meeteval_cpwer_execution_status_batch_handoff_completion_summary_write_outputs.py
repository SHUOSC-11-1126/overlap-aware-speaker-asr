from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_cpwer_execution_status_batch_handoff_completion_summary import (
    COMPLETION_COLUMNS,
    build_completion_summary_row,
    write_outputs,
)


class MeetEvalCpwerExecutionStatusBatchHandoffCompletionSummaryWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_completion_summary_artifacts(self) -> None:
        handoff_rows = [
            {"handoff_status": "execution_handoff_ready"},
            {"handoff_status": "execution_handoff_complete"},
            {"handoff_status": "execution_handoff_queued"},
        ]
        completion_row = build_completion_summary_row(handoff_rows)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.meeteval_cpwer_execution_status_batch_handoff_completion_summary.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(completion_row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, COMPLETION_COLUMNS)
                self.assertEqual(list(reader)[0]["queue_status"], "queue_ready_to_execute")
            self.assertIn("Handoff Completion Summary", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
