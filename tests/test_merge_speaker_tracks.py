from __future__ import annotations

import unittest

from src.merge_speaker_tracks import speaker_segments


class MergeSpeakerTracksSegmentExtractionTest(unittest.TestCase):
    def test_speaker_segments_filters_empty_text(self) -> None:
        transcript = {
            "segments": [
                {"start": 0.0, "end": 1.0, "text": " hello "},
                {"start": 1.0, "end": 2.0, "text": "   "},
            ]
        }
        segments = speaker_segments(transcript, "SPEAKER_1")
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["speaker"], "SPEAKER_1")
        self.assertEqual(segments[0]["text"], "hello")


if __name__ == "__main__":
    unittest.main()
