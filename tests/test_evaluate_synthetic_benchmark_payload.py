from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.config import PROJECT_ROOT
from src.evaluate_synthetic_benchmark import (
    build_cleaned_payload,
    build_raw_payload,
    build_speaker_payload,
    write_transcript,
)


class EvaluateSyntheticBenchmarkPayloadTest(unittest.TestCase):
    def test_build_raw_payload_includes_whisper_model_and_relative_audio_path(self) -> None:
        audio_path = PROJECT_ROOT / "resources" / "synthetic_overlap" / "audio" / "demo.wav"
        payload = build_raw_payload(
            "sample_001",
            "SyntheticNoOverlap",
            audio_path,
            "zh",
            "small",
            {"text": "示例", "segments": [{"text": "示例"}], "runtime_sec": 1.5},
            "mixed",
            split="train",
        )
        self.assertEqual(payload["sample_id"], "sample_001")
        self.assertEqual(payload["model"], "whisper-small")
        self.assertEqual(payload["mode"], "mixed")
        self.assertEqual(payload["split"], "train")
        self.assertTrue(payload["audio_path"].startswith("resources/"))

    def test_build_speaker_payload_merges_tracks_and_sums_runtime(self) -> None:
        spk1 = {
            "segments": [{"speaker": "SPEAKER_1", "start": 0.0, "end": 1.0, "text": "甲"}],
            "runtime_sec": 1.0,
        }
        spk2 = {
            "segments": [{"speaker": "SPEAKER_2", "start": 1.0, "end": 2.0, "text": "乙"}],
            "runtime_sec": 2.0,
        }
        payload = build_speaker_payload("sample_001", "SyntheticNoOverlap", "small", "zh", spk1, spk2)
        self.assertEqual(payload["method"], "separated_tracks_whisper")
        self.assertEqual(len(payload["segments"]), 2)
        self.assertEqual(payload["runtime_sec_total"], 3.0)
        self.assertIn("甲", payload["full_text"])

    def test_build_cleaned_payload_tracks_removed_count(self) -> None:
        speaker_payload = {
            "segments": [
                {"speaker": "SPEAKER_1", "start": 0.0, "end": 1.0, "text": "重复"},
                {"speaker": "SPEAKER_1", "start": 1.0, "end": 2.0, "text": "重复"},
            ]
        }
        source_path = PROJECT_ROOT / "results" / "synthetic_transcripts_speaker" / "sample_001_separated_speaker_transcript.json"
        payload = build_cleaned_payload("sample_001", "SyntheticNoOverlap", speaker_payload, source_path)
        self.assertEqual(payload["method"], "duplicate_suppression")
        self.assertGreaterEqual(payload["removed_count"], 0)
        self.assertTrue(payload["source_path"].endswith("sample_001_separated_speaker_transcript.json"))

    def test_write_transcript_creates_parent_dirs_and_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "nested" / "sample_001_mixed_whisper.json"
            write_transcript(output_path, {"sample_id": "sample_001", "text": "demo"})
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["sample_id"], "sample_001")


if __name__ == "__main__":
    unittest.main()
