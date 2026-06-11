from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_embedding_trial_execution_receipt_completion_dashboard_bridge_checklist import (
    BRIDGE_CHECKLIST_COLUMNS,
    build_bridge_checklist_rows,
    write_outputs,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptCompletionDashboardBridgeChecklistWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "current_case": "NoOverlap",
                "dashboard_note": "Template-only receipt coordination pending.",
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.speaker_profile_embedding_trial_execution_receipt_completion_dashboard_bridge_checklist.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(rows)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, BRIDGE_CHECKLIST_COLUMNS)
                self.assertEqual(list(reader)[0]["current_case"], "NoOverlap")
            self.assertIn(
                "Completion Dashboard Bridge Checklist",
                md_path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
