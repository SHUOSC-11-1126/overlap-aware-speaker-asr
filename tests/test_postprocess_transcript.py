from __future__ import annotations

import unittest

from src.postprocess_transcript import normalized_text, should_remove_segment, similarity


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


if __name__ == "__main__":
    unittest.main()
