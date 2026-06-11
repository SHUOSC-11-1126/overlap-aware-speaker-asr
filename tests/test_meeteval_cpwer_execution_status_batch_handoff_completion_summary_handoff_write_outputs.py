from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_cpwer_execution_status_batch_handoff_completion_summary_handoff import (
    HANDOFF_COLUMNS,
    build_handoff_rows,
    write_outputs,
)


class MeetEvalCpwerExecutionStatusBatchHandoffCompletionSummaryHandoffWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_handoff_artifacts(self) -> None:
        handoff_rows = build_handoff_rows(
            {"queue_status": "queue_complete", "complete_handoff_count": "5", "total_handoff_count": "5"}
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.meeteval_cpwer_execution_status_batch_handoff_completion_summary_handoff.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(handoff_rows)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, HANDOFF_COLUMNS)
                self.assertEqual(
                    list(reader)[0]["handoff_status"],
                    "batch_handoff_completion_handoff_ready",
                )
            self.assertIn("Completion Summary Handoff", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
