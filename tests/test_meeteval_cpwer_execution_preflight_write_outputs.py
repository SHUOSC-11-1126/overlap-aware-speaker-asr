from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_cpwer_execution_preflight import (
    PREFLIGHT_COLUMNS,
    build_receipt_rows,
    write_outputs,
)


class MeetEvalCpwerExecutionPreflightWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_preflight_and_receipt_artifacts(self) -> None:
        preflight_row = {
            "case_id": "NoOverlap",
            "handoff_status": "execution_handoff_ready",
            "scaffold_status": "scaffold_only",
            "hypothesis_source": "separated_whisper",
            "reference_segment_count": 2,
            "hypothesis_segment_count": 2,
            "speaker_set_match": True,
            "time_range_valid": True,
            "export_path_valid": True,
            "preflight_pass": True,
            "preflight_note": "Execution preflight validated for NoOverlap.",
        }
        receipt_rows = build_receipt_rows(preflight_row)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.meeteval_cpwer_execution_preflight.PROJECT_ROOT", root):
                outputs = write_outputs(preflight_row, receipt_rows)

            for path in outputs:
                self.assertTrue(path.exists())
            with outputs[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, PREFLIGHT_COLUMNS)
                self.assertEqual(list(reader)[0]["preflight_pass"], "True")
            self.assertIn("Execution Preflight", outputs[2].read_text(encoding="utf-8"))
            self.assertEqual(
                json.loads(outputs[3].read_text(encoding="utf-8"))[0]["execution_status"],
                "preflight_complete",
            )


if __name__ == "__main__":
    unittest.main()
