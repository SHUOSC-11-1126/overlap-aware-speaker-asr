from __future__ import annotations

import unittest

from src.router_ablation import (
    adjacent_repetition_from_segments,
    get_cleaned_closer_to_mixed,
    repetition_count_from_text,
    repetition_count_from_transcript,
    select_base_by_overlap,
    strategy_note,
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

    def test_adjacent_repetition_from_segments_counts_duplicates(self) -> None:
        count = adjacent_repetition_from_segments(
            [{"text": "重复"}, {"text": "重复"}, {"text": "不同"}]
        )
        self.assertEqual(count, 1)

    def test_select_base_by_overlap_matches_router_v1(self) -> None:
        method, _ = select_base_by_overlap(0)
        self.assertEqual(method, "separated_whisper")

    def test_strategy_note_describes_known_strategies(self) -> None:
        self.assertIn("Fixed baseline", strategy_note("fixed_mixed_whisper"))


if __name__ == "__main__":
    unittest.main()
