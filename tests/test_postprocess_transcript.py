from __future__ import annotations

import unittest

from src.postprocess_transcript import normalized_text, similarity


class PostprocessTranscriptNormalizationTest(unittest.TestCase):
    def test_normalized_text_strips_punctuation_and_whitespace(self) -> None:
        self.assertEqual(normalized_text("你好，世界！"), "你好世界")

    def test_similarity_is_high_for_near_duplicate_phrases(self) -> None:
        score = similarity("嗯嗯好的", "嗯嗯好的啊")
        self.assertGreaterEqual(score, 0.86)


if __name__ == "__main__":
    unittest.main()
