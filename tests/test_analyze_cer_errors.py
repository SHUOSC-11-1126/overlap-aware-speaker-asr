from __future__ import annotations

import unittest

from src.analyze_cer_errors import find_repeated_phrases


class AnalyzeCerErrorsPhraseDetectionTest(unittest.TestCase):
    def test_find_repeated_phrases_detects_repeated_clause(self) -> None:
        text = "你好世界\n你好世界\n其他内容"
        phrases = find_repeated_phrases(text)
        types = {item["type"] for item in phrases}
        self.assertIn("repeated_clause", types)

    def test_find_repeated_phrases_detects_high_frequency_chunk(self) -> None:
        text = "abababababab"
        phrases = find_repeated_phrases(text)
        types = {item["type"] for item in phrases}
        self.assertIn("high_frequency_chunk", types)


if __name__ == "__main__":
    unittest.main()
