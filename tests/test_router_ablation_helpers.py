from __future__ import annotations

import unittest

from src.router_ablation import (
    get_cleaned_closer_to_mixed,
    repetition_count_from_text,
    repetition_count_from_transcript,
)


class RouterAblationHelpersTest(unittest.TestCase):
    def test_get_cleaned_closer_to_mixed_compares_length_distance(self) -> None:
        self.assertTrue(get_cleaned_closer_to_mixed(mixed_len=100, separated_len=200, cleaned_len=110))
        self.assertFalse(get_cleaned_closer_to_mixed(mixed_len=100, separated_len=120, cleaned_len=150))

    def test_repetition_count_from_text_detects_repeated_chunks(self) -> None:
        text = "同意这个观点同意这个观点"
        self.assertGreater(repetition_count_from_text(text), 0)

    def test_repetition_count_from_transcript_includes_adjacent_segments(self) -> None:
        count = repetition_count_from_transcript(
            "重复句子重复句子",
            [{"text": "重复句子"}, {"text": "重复句子"}],
        )
        self.assertGreaterEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
