from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_cpwer_execution_status_batch_handoff import (
    HANDOFF_COLUMNS,
    build_handoff_receipt_rows,
    build_handoff_rows,
    write_outputs,
)


class MeetEvalCpwerExecutionStatusBatchHandoffWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_handoff_and_receipt_artifacts(self) -> None:
        status_rows = [
            {"case_id": "NoOverlap", "execution_chain_status": "execution_chain_ready"},
            {"case_id": "HeavyOverlap", "execution_chain_status": "execution_chain_in_progress"},
        ]
        preflight_rows = [
            {"case_id": "NoOverlap", "hypothesis_source": "separated_whisper"},
            {"case_id": "HeavyOverlap", "hypothesis_source": "separated_whisper_cleaned"},
        ]
        handoff_rows = build_handoff_rows(status_rows, preflight_rows)
        receipt_rows = build_handoff_receipt_rows(handoff_rows)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.meeteval_cpwer_execution_status_batch_handoff.PROJECT_ROOT", root):
                outputs = write_outputs(handoff_rows, receipt_rows)

            for path in outputs:
                self.assertTrue(path.exists())
            with outputs[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, HANDOFF_COLUMNS)
                rows = list(reader)
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0]["handoff_status"], "execution_handoff_ready")
            self.assertEqual(
                json.loads(outputs[3].read_text(encoding="utf-8"))[0]["execution_status"],
                "batch_handoff_documented",
            )


if __name__ == "__main__":
    unittest.main()
