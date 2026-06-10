from __future__ import annotations

import unittest
from pathlib import Path

from src.config import PROJECT_ROOT
from src.transcribe_whisper import read_json


class TranscribeWhisperReadJsonTest(unittest.TestCase):
    def test_read_json_loads_existing_transcript(self) -> None:
        path = PROJECT_ROOT / "results" / "transcripts_raw" / "NoOverlap_mixed_whisper.json"
        payload = read_json(path)
        self.assertIn("text", payload)

    def test_read_json_raises_for_missing_file(self) -> None:
        missing = PROJECT_ROOT / "results" / "__missing_transcribe_whisper__.json"
        with self.assertRaises(FileNotFoundError):
            read_json(missing)


if __name__ == "__main__":
    unittest.main()
