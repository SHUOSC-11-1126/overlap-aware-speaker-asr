from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_text_proxy_trial_diagnostic import (
    DIAGNOSTIC_COLUMNS,
    SUMMARY_COLUMNS,
    build_diagnostic_rows,
    build_summary_row,
    write_outputs,
)


class SpeakerProfileTextProxyTrialDiagnosticWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_diagnostic_and_summary_artifacts(self) -> None:
        diagnostic_rows = build_diagnostic_rows(
            [
                {
                    "case_id": "NoOverlap",
                    "best_profile_alignment": "swapped",
                    "profile_confidence_gap": "0.24",
                }
            ]
        )
        summary_row = build_summary_row(diagnostic_rows)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.speaker_profile_text_proxy_trial_diagnostic.PROJECT_ROOT", root):
                paths = write_outputs(diagnostic_rows, summary_row)

            for path in paths:
                self.assertTrue(path.exists())
            with paths[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, DIAGNOSTIC_COLUMNS)
                self.assertEqual(list(reader)[0]["diagnostic_status"], "text_proxy_diagnostic_complete")
            payload = json.loads(paths[1].read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["case_id"], "NoOverlap")
            self.assertIn("Text-Proxy Trial Diagnostic", paths[2].read_text(encoding="utf-8"))
            with paths[3].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SUMMARY_COLUMNS)
                self.assertEqual(list(reader)[0]["swapped_count"], "1")


if __name__ == "__main__":
    unittest.main()
