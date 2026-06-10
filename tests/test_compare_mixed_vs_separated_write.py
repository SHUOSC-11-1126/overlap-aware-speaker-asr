from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.compare_mixed_vs_separated import CSV_COLUMNS, write_csv, write_json


def _sample_row() -> dict[str, str]:
    return {
        "case_id": "FixtureCase",
        "overlap_level": "0",
        "model": "tiny",
        "mixed_audio_path": "audio/mixed.wav",
        "separated_method": "separated_tracks_whisper",
        "mixed_runtime_sec": "1.0",
        "separated_runtime_sec": "2.0",
        "mixed_segments_count": "3",
        "separated_segments_count": "4",
        "mixed_text_length": "100",
        "separated_text_length": "90",
        "mixed_text_preview": "混合",
        "separated_text_preview": "分离",
        "mixed_transcript_path": "results/transcripts_raw/FixtureCase_mixed_whisper.json",
        "separated_transcript_path": "results/transcripts_speaker/FixtureCase_separated_speaker_transcript.json",
    }


class CompareMixedVsSeparatedWriteTest(unittest.TestCase):
    def test_write_csv_writes_expected_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "compare.csv"
            write_csv([_sample_row()], csv_path)
            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, CSV_COLUMNS)
                rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["case_id"], "FixtureCase")

    def test_write_json_round_trips_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = Path(tmp_dir) / "compare.json"
            write_json([_sample_row()], json_path)
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["model"], "tiny")


if __name__ == "__main__":
    unittest.main()
