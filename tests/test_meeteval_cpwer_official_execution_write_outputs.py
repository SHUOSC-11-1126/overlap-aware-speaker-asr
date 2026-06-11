from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_cpwer_official_execution import (
    EXECUTION_COLUMNS,
    build_execution_row,
    write_outputs,
)


class MeetEvalCpwerOfficialExecutionWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_execution_artifacts(self) -> None:
        rows = [
            build_execution_row("NoOverlap", "separated_whisper", 0.12, 2, True, scored_length=10),
            build_execution_row("HeavyOverlap", "separated_whisper_cleaned", None, 2, False),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.meeteval_cpwer_official_execution.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(rows)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, EXECUTION_COLUMNS)
                parsed = list(reader)
                self.assertEqual(parsed[0]["execution_status"], "official_cpwer_narrow_dry_run_complete")
                self.assertEqual(parsed[1]["execution_status"], "official_cpwer_tool_unavailable")
            self.assertIn("Official Execution", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
