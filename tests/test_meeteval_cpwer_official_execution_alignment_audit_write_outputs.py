from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_cpwer_official_execution_alignment_audit import (
    ALIGNMENT_COLUMNS,
    build_alignment_rows,
    write_outputs,
)


class MeetEvalCpwerOfficialExecutionAlignmentAuditWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_alignment_audit_artifacts(self) -> None:
        execution_rows = [
            {"case_id": "NoOverlap", "official_cpwer": "0.12"},
            {"case_id": "HeavyOverlap", "official_cpwer": "0.25"},
        ]
        bridge_lite_by_case = {"NoOverlap": "0.12", "HeavyOverlap": "0.18"}
        rows = build_alignment_rows(execution_rows, bridge_lite_by_case)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.meeteval_cpwer_official_execution_alignment_audit.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(rows)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, ALIGNMENT_COLUMNS)
                parsed = list(reader)
                self.assertEqual(parsed[0]["alignment_status"], "aligned")
                self.assertEqual(parsed[1]["alignment_status"], "moderate_drift")
            self.assertIn("Alignment Audit", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
