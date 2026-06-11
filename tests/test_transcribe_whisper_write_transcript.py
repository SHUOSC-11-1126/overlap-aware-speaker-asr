from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.transcribe_whisper import write_transcript


class TranscribeWhisperWriteTranscriptTest(unittest.TestCase):
    def test_write_transcript_emits_json_payload_with_model_and_segments(self) -> None:
        result = {
            "text": "你好世界",
            "segments": [{"start": 0.0, "end": 1.0, "text": "你好世界"}],
            "runtime_sec": 1.5,
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            audio_path = root / "audio" / "FixtureCase.wav"
            audio_path.parent.mkdir(parents=True)
            audio_path.write_bytes(b"wav")
            with patch("src.transcribe_whisper.PROJECT_ROOT", root):
                output_path = write_transcript(
                    case_id="FixtureCase",
                    audio_path=audio_path,
                    model_name="small",
                    language="zh",
                    result=result,
                    mode="mixed",
                )

            self.assertTrue(output_path.exists())
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["case_id"], "FixtureCase")
            self.assertEqual(payload["model"], "whisper-small")
            self.assertEqual(payload["text"], "你好世界")
            self.assertEqual(payload["segments"][0]["text"], "你好世界")


if __name__ == "__main__":
    unittest.main()
