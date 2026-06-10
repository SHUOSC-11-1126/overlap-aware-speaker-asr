from __future__ import annotations

import unittest

from src.merge_speaker_tracks import build_full_text, speaker_segments


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


class MergeSpeakerTracksFullTextTest(unittest.TestCase):
    def test_build_full_text_joins_speaker_lines(self) -> None:
        segments = [
            {"speaker": "SPEAKER_1", "text": "first"},
            {"speaker": "SPEAKER_2", "text": "second"},
        ]
        self.assertEqual(build_full_text(segments), "[SPEAKER_1] first\n[SPEAKER_2] second")


if __name__ == "__main__":
    unittest.main()
