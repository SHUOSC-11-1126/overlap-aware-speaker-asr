from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.merge_speaker_tracks import build_separated_benchmark_rows


class MergeSpeakerTracksBuildSeparatedBenchmarkTest(unittest.TestCase):
    def test_build_separated_benchmark_rows_aggregates_runtime_and_segment_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
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
            (raw_dir / "FixtureCase_spk1_whisper.json").write_text(
                json.dumps(spk1_payload), encoding="utf-8"
            )
            (raw_dir / "FixtureCase_spk2_whisper.json").write_text(
                json.dumps(spk2_payload), encoding="utf-8"
            )
            (speaker_dir / "FixtureCase_separated_speaker_transcript.json").write_text(
                json.dumps(merged_payload), encoding="utf-8"
            )

            config = {"audio_cases": [{"id": "FixtureCase", "overlap_level": 0}]}
            with patch("src.merge_speaker_tracks.PROJECT_ROOT", root):
                rows = build_separated_benchmark_rows(config)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["case_id"], "FixtureCase")
        self.assertEqual(row["spk1_segments_count"], 1)
        self.assertEqual(row["spk2_segments_count"], 1)
        self.assertEqual(row["merged_segments_count"], 2)
        self.assertEqual(row["runtime_sec_total"], 3.5)
        self.assertEqual(row["spk1_runtime_sec"], 1.2)
        self.assertEqual(row["spk2_runtime_sec"], 2.3)
        self.assertTrue(row["speaker_transcript_path"].endswith("FixtureCase_separated_speaker_transcript.json"))


if __name__ == "__main__":
    unittest.main()
