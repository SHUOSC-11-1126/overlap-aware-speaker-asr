from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.evaluate_speaker_cer import load_speaker_transcript, read_existing_rows


class EvaluateSpeakerCerReadExistingTest(unittest.TestCase):
    def test_read_existing_rows_returns_empty_for_missing_path(self) -> None:
        self.assertEqual(read_existing_rows(Path("/tmp/__missing_speaker_cer_table__.csv")), [])

    def test_read_existing_rows_reads_csv_and_json_rows_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "rows.csv"
            json_path = Path(tmp_dir) / "rows.json"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["case_id", "method", "cer"])
                writer.writeheader()
                writer.writerow({"case_id": "NoOverlap", "method": "separated_whisper", "cer": "0.1"})
            json_path.write_text(
                json.dumps({"rows": [{"case_id": "LightOverlap", "method": "mixed_whisper", "cer": 0.2}]}),
                encoding="utf-8",
            )

            csv_rows = read_existing_rows(csv_path)
            json_rows = read_existing_rows(json_path)

        self.assertEqual(csv_rows[0]["case_id"], "NoOverlap")
        self.assertEqual(json_rows[0]["method"], "mixed_whisper")

    def test_load_speaker_transcript_raises_for_unsupported_method(self) -> None:
        with self.assertRaises(ValueError):
            load_speaker_transcript("NoOverlap", "mixed_whisper")

    def test_load_speaker_transcript_loads_separated_transcript_for_no_overlap(self) -> None:
        path, payload = load_speaker_transcript("NoOverlap", "separated_whisper")
        self.assertTrue(path.name.endswith("_separated_speaker_transcript.json"))
        self.assertIn("segments", payload)


if __name__ == "__main__":
    unittest.main()
