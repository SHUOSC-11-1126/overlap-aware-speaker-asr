from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_cpwer_alignment import (
    ALIGNMENT_COLUMNS,
    SUMMARY_COLUMNS,
    build_alignment_row,
    build_alignment_summary_row,
    write_outputs,
)


class MeetEvalCpwerAlignmentWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_alignment_and_summary_artifacts(self) -> None:
        alignment_rows = [
            build_alignment_row(
                {"case_id": "NoOverlap", "hypothesis_source": "separated_whisper", "cpwer_bridge_lite": 0.1},
                speaker_macro_cer=0.1,
            ),
            build_alignment_row(
                {"case_id": "HeavyOverlap", "hypothesis_source": "separated_whisper_cleaned", "cpwer_bridge_lite": 0.2},
                speaker_macro_cer=0.25,
            ),
        ]
        summary_row = build_alignment_summary_row(alignment_rows)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.meeteval_cpwer_alignment.PROJECT_ROOT", root):
                outputs = write_outputs(alignment_rows, summary_row)

            for path in outputs:
                self.assertTrue(path.exists())
            with outputs[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, ALIGNMENT_COLUMNS)
                rows = list(reader)
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0]["alignment_status"], "matched")
                self.assertEqual(rows[1]["alignment_status"], "drift")
            with outputs[3].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SUMMARY_COLUMNS)
            self.assertIn("MeetEval cpWER Alignment", outputs[2].read_text(encoding="utf-8"))
            self.assertEqual(json.loads(outputs[4].read_text(encoding="utf-8"))["matched_count"], 1)


if __name__ == "__main__":
    unittest.main()
