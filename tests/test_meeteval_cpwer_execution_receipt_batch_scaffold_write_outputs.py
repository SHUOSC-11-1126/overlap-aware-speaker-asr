from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_cpwer_execution_receipt_batch_scaffold import (
    SCAFFOLD_COLUMNS,
    build_scaffold_receipt_rows,
    build_scaffold_rows,
    write_outputs,
)


class MeetEvalCpwerExecutionReceiptBatchScaffoldWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_batch_scaffold_receipt_template_and_receipt_artifacts(self) -> None:
        scaffold_rows = build_scaffold_rows(
            [
                {"case_id": "NoOverlap", "preflight_pass": True, "hypothesis_source": "separated_whisper"},
                {"case_id": "HeavyOverlap", "preflight_pass": False, "hypothesis_source": "separated_whisper_cleaned"},
            ]
        )
        receipt_rows = build_scaffold_receipt_rows(scaffold_rows)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.meeteval_cpwer_execution_receipt_batch_scaffold.PROJECT_ROOT", root):
                outputs = write_outputs(scaffold_rows, receipt_rows)

            for path in outputs:
                self.assertTrue(path.exists())
            with outputs[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SCAFFOLD_COLUMNS)
                self.assertEqual(len(list(reader)), 2)
            self.assertEqual(len(json.loads(outputs[3].read_text(encoding="utf-8"))), 2)
            self.assertEqual(
                json.loads(outputs[4].read_text(encoding="utf-8"))[0]["execution_status"],
                "receipt_batch_scaffold_complete",
            )


if __name__ == "__main__":
    unittest.main()
