from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.external_validation_slice_staging_execution_status import (
    STATUS_COLUMNS,
    build_status_row,
    write_outputs,
)


class ExternalValidationSliceStagingExecutionStatusBuildRowTest(unittest.TestCase):
    def test_build_status_row_marks_chain_ready_when_scaffold_only_and_blocker_present(self) -> None:
        row = build_status_row(
            {"dataset_name": "FixtureDataset", "handoff_status": "staging_handoff_ready", "blocker": "license"},
            {"scaffold_status": "receipt_scaffold_only"},
            "scaffold_only",
        )
        self.assertEqual(row["dataset_name"], "FixtureDataset")
        self.assertEqual(row["execution_chain_status"], "execution_chain_ready")

    def test_build_status_row_marks_in_progress_when_scaffold_missing(self) -> None:
        row = build_status_row(
            {"dataset_name": "FixtureDataset", "blocker": "license"},
            {"scaffold_status": "missing"},
            "missing",
        )
        self.assertEqual(row["execution_chain_status"], "execution_chain_in_progress")


class ExternalValidationSliceStagingExecutionStatusWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        row = build_status_row(
            {"dataset_name": "FixtureDataset", "blocker": "license"},
            {"scaffold_status": "receipt_scaffold_only"},
            "scaffold_only",
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.external_validation_slice_staging_execution_status.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(row)

            self.assertTrue(csv_path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, STATUS_COLUMNS)
                self.assertEqual(list(reader)[0]["dataset_name"], "FixtureDataset")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["scope"], "external_validation_slice_staging_execution_chain")
            self.assertIn("External Validation Slice Staging Execution Status", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
