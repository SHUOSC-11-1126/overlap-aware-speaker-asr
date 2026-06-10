from __future__ import annotations

import unittest

from src.merge_speaker_tracks import read_transcript


class MergeSpeakerTracksReadTranscriptTest(unittest.TestCase):
    def test_read_transcript_loads_existing_spk1_file(self) -> None:
        payload = read_transcript("NoOverlap", 1)
        self.assertIn("segments", payload)
        self.assertTrue(payload.get("text", "").strip())

    def test_read_transcript_raises_for_missing_case(self) -> None:
        with self.assertRaises(FileNotFoundError):
            read_transcript("__missing_case__", 1)


if __name__ == "__main__":
    unittest.main()
