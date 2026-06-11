from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_embedding_trial_execution_receipt_completion_dashboard import (
    DASHBOARD_COLUMNS,
    build_dashboard_row,
    write_outputs,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptCompletionDashboardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_dashboard_artifacts(self) -> None:
        row = build_dashboard_row(
            {
                "operator_case": "NoOverlap",
                "operator_status": "receipt_not_ready",
            },
            {
                "next_milestone": "fill_execution_receipt",
                "remaining_gate_count": "3",
            },
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.speaker_profile_embedding_trial_execution_receipt_completion_dashboard.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, DASHBOARD_COLUMNS)
                self.assertEqual(list(reader)[0]["current_case"], "NoOverlap")
            self.assertIn(
                "Completion Dashboard",
                md_path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
