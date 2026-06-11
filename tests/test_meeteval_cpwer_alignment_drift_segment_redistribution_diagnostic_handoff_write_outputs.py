from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_handoff import (
    HANDOFF_COLUMNS,
    build_handoff_receipt_rows,
    build_handoff_row,
    write_outputs,
)


class MeetEvalCpwerAlignmentDriftSegmentRedistributionDiagnosticHandoffWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_handoff_and_receipt_artifacts(self) -> None:
        handoff_row = build_handoff_row(
            {"case_id": "HeavyOverlap", "redistribution_mismatch_count": "1", "dominant_blocker": "SPEAKER_1 hypothesis_split"}
        )
        receipt_rows = build_handoff_receipt_rows(handoff_row)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_handoff.PROJECT_ROOT",
                root,
            ):
                outputs = write_outputs(handoff_row, receipt_rows)

            for path in outputs:
                self.assertTrue(path.exists())
            with outputs[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, HANDOFF_COLUMNS)
                self.assertEqual(list(reader)[0]["handoff_status"], "redistribution_handoff_ready")
            self.assertIn("Redistribution Diagnostic Handoff", outputs[2].read_text(encoding="utf-8"))
            self.assertEqual(json.loads(outputs[3].read_text(encoding="utf-8"))[0]["execution_status"], "handoff_documented")


if __name__ == "__main__":
    unittest.main()
