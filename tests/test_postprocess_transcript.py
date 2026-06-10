from __future__ import annotations

import unittest

from src.postprocess_transcript import (
    build_full_text,
    normalized_text,
    process_segments,
    should_remove_segment,
    similarity,
)


class PostprocessTranscriptNormalizationTest(unittest.TestCase):
    def test_normalized_text_strips_punctuation_and_whitespace(self) -> None:
        self.assertEqual(normalized_text("你好，世界！"), "你好世界")

    def test_similarity_is_high_for_near_duplicate_phrases(self) -> None:
        score = similarity("嗯嗯好的", "嗯嗯好的啊")
        self.assertGreaterEqual(score, 0.86)


class PostprocessTranscriptDuplicateDetectionTest(unittest.TestCase):
    def test_should_remove_segment_flags_exact_adjacent_duplicate(self) -> None:
        first = {"speaker": "S1", "text": "重复一句"}
        second = {"speaker": "S1", "text": "重复一句"}
        remove, reason = should_remove_segment(second, [first], {"S1": [first]})
        self.assertTrue(remove)
        self.assertEqual(reason, "exact_duplicate_adjacent")


class PostprocessTranscriptSegmentPipelineTest(unittest.TestCase):
    def test_process_segments_removes_empty_text(self) -> None:
        segments = [
            {"speaker": "S1", "text": "保留"},
            {"speaker": "S1", "text": "   "},
        ]
        cleaned, removed = process_segments(segments)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0]["reason"], "empty_text")

    def test_build_full_text_formats_speaker_labels(self) -> None:
        text = build_full_text([{"speaker": "A", "text": "hello"}])
        self.assertEqual(text, "[A] hello")


if __name__ == "__main__":
    unittest.main()
