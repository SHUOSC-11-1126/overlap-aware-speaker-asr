from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_multisignal_diagnostic import (
    DIAGNOSTIC_COLUMNS,
    SUMMARY_COLUMNS,
    write_outputs,
)


def _sample_diagnostic_row() -> dict[str, str]:
    return {
        "case_id": "FixtureCase",
        "hypothesis_source": "separated_whisper",
        "text_best_alignment": "direct",
        "audio_best_alignment": "direct",
        "text_confidence_gap": "0.42",
        "audio_confidence_gap": "0.01",
        "alignment_agreement": "agree",
        "audio_support_level": "separable_support",
        "combined_signal_status": "text_direct_audio_ok",
        "recommended_next_step": "fixture next step",
        "result_label": "experimental/frontier",
        "observation": "fixture",
    }


def _sample_summary_row() -> dict[str, str]:
    return {
        "case_count": "1",
        "agreement_count": "1",
        "weak_support_count": "0",
        "frontier_decision": "continue_multisignal_probe",
        "summary_note": "fixture summary",
    }


class SpeakerProfileMultisignalDiagnosticWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_diagnostic_and_summary_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.speaker_profile_multisignal_diagnostic.PROJECT_ROOT", root):
                outputs = write_outputs([_sample_diagnostic_row()], _sample_summary_row())

            for path in outputs:
                self.assertTrue(path.exists(), msg=str(path))

            csv_path, json_path, md_path, summary_csv, summary_json, summary_md = outputs
            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, DIAGNOSTIC_COLUMNS)
                self.assertEqual(list(reader)[0]["case_id"], "FixtureCase")

            with summary_csv.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SUMMARY_COLUMNS)
                self.assertEqual(list(reader)[0]["frontier_decision"], "continue_multisignal_probe")

            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))[0]["alignment_agreement"], "agree")
            self.assertIn("Multi-signal Diagnostic", md_path.read_text(encoding="utf-8"))
            self.assertIn("Multi-signal Summary", summary_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
