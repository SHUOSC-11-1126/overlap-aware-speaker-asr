from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.merge_speaker_tracks import write_separated_benchmark


def _write_fixture_transcripts(root: Path) -> None:
    raw_dir = root / "results" / "transcripts_raw"
    speaker_dir = root / "results" / "transcripts_speaker"
    raw_dir.mkdir(parents=True)
    speaker_dir.mkdir(parents=True)

    spk1_payload = {
        "model": "tiny",
        "audio_path": "audio/spk1.wav",
        "runtime_sec": 1.2,
        "text": "你好",
        "segments": [{"start": 0.0, "end": 1.0, "text": "你好"}],
    }
    spk2_payload = {
        "model": "tiny",
        "audio_path": "audio/spk2.wav",
        "runtime_sec": 2.3,
        "text": "世界",
        "segments": [{"start": 1.0, "end": 2.0, "text": "世界"}],
    }
    merged_payload = {
        "model": "tiny",
        "runtime_sec_total": 3.5,
        "full_text": "[SPEAKER_1] 你好\n[SPEAKER_2] 世界",
        "segments": [
            {"speaker": "SPEAKER_1", "start": 0.0, "end": 1.0, "text": "你好"},
            {"speaker": "SPEAKER_2", "start": 1.0, "end": 2.0, "text": "世界"},
        ],
    }
    (raw_dir / "FixtureCase_spk1_whisper.json").write_text(json.dumps(spk1_payload), encoding="utf-8")
    (raw_dir / "FixtureCase_spk2_whisper.json").write_text(json.dumps(spk2_payload), encoding="utf-8")
    (speaker_dir / "FixtureCase_separated_speaker_transcript.json").write_text(
        json.dumps(merged_payload), encoding="utf-8"
    )


class MergeSpeakerTracksWriteSeparatedBenchmarkTest(unittest.TestCase):
    def test_write_separated_benchmark_emits_csv_and_json_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_fixture_transcripts(root)
            config = {"audio_cases": [{"id": "FixtureCase", "overlap_level": 0}]}
            with patch("src.merge_speaker_tracks.PROJECT_ROOT", root):
                write_separated_benchmark(config)

            csv_path = root / "results" / "tables" / "separated_asr_benchmark.csv"
            json_path = root / "results" / "tables" / "separated_asr_benchmark.json"
            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())

            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["case_id"], "FixtureCase")
            self.assertEqual(rows[0]["merged_segments_count"], "2")
            self.assertEqual(rows[0]["runtime_sec_total"], "3.5")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["overlap_level"], 0)
            self.assertIn("speaker_transcript_path", payload[0])


if __name__ == "__main__":
    unittest.main()
