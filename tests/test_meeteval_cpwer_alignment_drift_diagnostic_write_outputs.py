from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_cpwer_alignment_drift_diagnostic import (
    DIAGNOSTIC_COLUMNS,
    build_drift_diagnostic_receipt_rows,
    build_drift_diagnostic_row,
    write_outputs,
)


class MeetEvalCpwerAlignmentDriftDiagnosticWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_diagnostic_and_receipt_artifacts(self) -> None:
        diagnostic_rows = [
            build_drift_diagnostic_row(
                {
                    "case_id": "HeavyOverlap",
                    "hypothesis_source": "separated_whisper_cleaned",
                    "cpwer_bridge_lite": 0.162827,
                    "speaker_macro_cer": 0.146535,
                    "alignment_gap": 0.016292,
                }
            )
        ]
        receipt_rows = build_drift_diagnostic_receipt_rows(diagnostic_rows)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.meeteval_cpwer_alignment_drift_diagnostic.PROJECT_ROOT", root):
                outputs = write_outputs(diagnostic_rows, receipt_rows)

            for path in outputs:
                self.assertTrue(path.exists())
            with outputs[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, DIAGNOSTIC_COLUMNS)
                self.assertEqual(list(reader)[0]["case_id"], "HeavyOverlap")
            self.assertIn("MeetEval cpWER Alignment Drift Diagnostic", outputs[2].read_text(encoding="utf-8"))
            self.assertEqual(json.loads(outputs[3].read_text(encoding="utf-8"))[0]["drift_case_count"], "1")


if __name__ == "__main__":
    unittest.main()
