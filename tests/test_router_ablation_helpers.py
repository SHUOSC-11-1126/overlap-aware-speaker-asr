from __future__ import annotations

import unittest

import csv
import tempfile
from pathlib import Path

from src.router_ablation import (
    adjacent_repetition_from_segments,
    choose_strategy,
    get_cleaned_closer_to_mixed,
    load_cer_lookup,
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

    def test_choose_strategy_length_ratio_only_falls_back_on_inflation(self) -> None:
        method, rule = choose_strategy(
            "length_ratio_only",
            overlap_level=0,
            mixed_text_len=100,
            separated_text_len=200,
            cleaned_text_len=0,
            repetition_count=0,
            duplicate_removed_count=0,
            cleaned_exists=False,
            cleaned_closer_to_mixed=False,
            mixed_segments_count=3,
            separated_runtime_ratio=1.0,
        )
        self.assertEqual(method, "mixed_whisper")
        self.assertIn("length-inflated", rule)

    def test_load_cer_lookup_indexes_case_method_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "cer.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["case_id", "method", "cer"])
                writer.writeheader()
                writer.writerow({"case_id": "NoOverlap", "method": "mixed_whisper", "cer": "0.21"})

            lookup = load_cer_lookup(csv_path, "case_id")
            self.assertEqual(lookup[("NoOverlap", "mixed_whisper")], 0.21)


if __name__ == "__main__":
    unittest.main()
