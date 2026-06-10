from __future__ import annotations

import unittest

from src.evaluate_error_types import detect_repetition, dominant_error_type


class EvaluateErrorTypesHelpersTest(unittest.TestCase):
    def test_dominant_error_type_prefers_highest_count(self) -> None:
        self.assertEqual(dominant_error_type(1, 5, 2, repetition_count=0), "deletion")
        self.assertEqual(dominant_error_type(1, 1, 4, repetition_count=2), "insertion")

    def test_detect_repetition_counts_adjacent_duplicates(self) -> None:
        payload = {
            "segments": [
                {"text": "重复句子"},
                {"text": "重复句子"},
                {"text": "其他内容"},
            ]
        }
        count = detect_repetition(payload, "separated_whisper")
        self.assertGreaterEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
