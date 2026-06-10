from __future__ import annotations

import unittest

from src.config import load_config
from src.merge_speaker_tracks import build_full_text, find_case, speaker_segments


class MergeSpeakerTracksHelpersTest(unittest.TestCase):
    def test_speaker_segments_tags_and_filters_empty_text(self) -> None:
        segments = speaker_segments(
            {
                "segments": [
                    {"start": 0.0, "end": 1.0, "text": "  你好  "},
                    {"start": 1.0, "end": 2.0, "text": "   "},
                ]
            },
            "SPEAKER_1",
        )
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["speaker"], "SPEAKER_1")
        self.assertEqual(segments[0]["text"], "你好")

    def test_build_full_text_formats_speaker_labels(self) -> None:
        text = build_full_text(
            [
                {"speaker": "SPEAKER_1", "text": "第一句"},
                {"speaker": "SPEAKER_2", "text": "第二句"},
            ]
        )
        self.assertEqual(text, "[SPEAKER_1] 第一句\n[SPEAKER_2] 第二句")

    def test_find_case_returns_matching_audio_case(self) -> None:
        config = load_config()
        case = find_case(config, "LightOverlap")
        self.assertEqual(case["id"], "LightOverlap")


if __name__ == "__main__":
    unittest.main()
