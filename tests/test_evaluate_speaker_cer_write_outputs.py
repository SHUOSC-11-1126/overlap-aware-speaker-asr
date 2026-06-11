from __future__ import annotations

import csv
import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from src.evaluate_speaker_cer import write_outputs


class EvaluateSpeakerCerWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_writes_csv_and_json_tables(self) -> None:
        rows = [
            {
                "case_id": "NoOverlap",
                "method": "mixed_whisper",
                "speaker_1_cer": 0.1,
                "speaker_2_cer": 0.2,
                "speaker_macro_cer": 0.15,
                "speaker_gap": 0.1,
                "speaker_1_reference_length": 10,
                "speaker_2_reference_length": 12,
                "speaker_1_hypothesis_length": 9,
                "speaker_2_hypothesis_length": 11,
                "observation": "stable/gold speaker-aware CER",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with unittest.mock.patch("src.evaluate_speaker_cer.PROJECT_ROOT", root):
                csv_path, json_path = write_outputs(rows)
                with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                    loaded_csv = list(csv.DictReader(handle))
                loaded_json = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(loaded_csv[0]["case_id"], "NoOverlap")
        self.assertEqual(loaded_csv[0]["method"], "mixed_whisper")
        self.assertEqual(loaded_json, rows)


if __name__ == "__main__":
    unittest.main()
