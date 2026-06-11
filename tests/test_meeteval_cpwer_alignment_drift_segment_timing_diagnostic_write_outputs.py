from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_cpwer_alignment_drift_segment_timing_diagnostic import (
    SPEAKER_COLUMNS,
    SUMMARY_COLUMNS,
    build_receipt_row,
    build_speaker_rows,
    build_summary_row,
    write_outputs,
)


class MeetEvalCpwerAlignmentDriftSegmentTimingDiagnosticWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_speaker_summary_and_receipt_artifacts(self) -> None:
        speaker_rows = build_speaker_rows(
            "HeavyOverlap",
            {"SPEAKER_1": 1.0, "SPEAKER_2": 1.0},
            {"SPEAKER_1": 1.0, "SPEAKER_2": 1.5},
        )
        summary = build_summary_row("HeavyOverlap", speaker_rows)
        receipt_row = build_receipt_row(summary)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.meeteval_cpwer_alignment_drift_segment_timing_diagnostic.PROJECT_ROOT", root):
                outputs = write_outputs(speaker_rows, summary, receipt_row)

            for path in outputs:
                self.assertTrue(path.exists())
            with outputs[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SPEAKER_COLUMNS)
                self.assertEqual(len(list(reader)), 2)
            with outputs[3].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SUMMARY_COLUMNS)
            self.assertEqual(
                json.loads(outputs[6].read_text(encoding="utf-8"))[0]["execution_status"],
                "timing_diagnostic_complete",
            )


if __name__ == "__main__":
    unittest.main()
