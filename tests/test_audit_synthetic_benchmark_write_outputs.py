from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.audit_synthetic_benchmark import CSV_COLUMNS, write_outputs


def _sample_audit_row() -> dict[str, object]:
    return {
        "sample_id": "syn_fixture",
        "tier": "SyntheticNoOverlap",
        "method": "mixed_whisper",
        "cer": 0.9,
        "reference_length": 100,
        "hypothesis_length": 160,
        "length_ratio": 1.6,
        "source_snippet_filenames": "con_001.wav, pro_001.wav",
        "mixed_audio_path": "audio/mixed.wav",
        "spk1_audio_path": "audio/spk1.wav",
        "spk2_audio_path": "audio/spk2.wav",
        "hypothesis_preview": "假设",
        "reference_preview": "参考",
        "suspected_issue": "high_length_ratio",
    }


class AuditSyntheticBenchmarkWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.audit_synthetic_benchmark.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs([_sample_audit_row()])

            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())

            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, CSV_COLUMNS)
                rows = list(reader)
            self.assertEqual(rows[0]["sample_id"], "syn_fixture")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["suspected_issue"], "high_length_ratio")

            markdown = md_path.read_text(encoding="utf-8")
            self.assertIn("Synthetic Benchmark Sanity Audit", markdown)
            self.assertIn("syn_fixture", markdown)


if __name__ == "__main__":
    unittest.main()
