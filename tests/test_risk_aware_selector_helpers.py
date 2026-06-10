from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from src.risk_aware_selector import (
    adjacent_repeat_count,
    aggregate_speaker_text,
    choose_final_method,
    classify_risk,
    load_case_ids,
    load_map,
    load_table,
    repeat_phrase_count,
    speaker_lengths_from_segments,
)


class RiskAwareSelectorHelpersTest(unittest.TestCase):
    def test_aggregate_speaker_text_joins_matching_segments(self) -> None:
        text = aggregate_speaker_text(
            [
                {"speaker": "SPEAKER_1", "text": "你好"},
                {"speaker": "SPEAKER_2", "text": "世界"},
                {"speaker": "SPEAKER_1", "text": "再见"},
            ],
            "SPEAKER_1",
        )
        self.assertEqual(text, "你好再见")

    def test_repeat_phrase_count_detects_repeated_chunks(self) -> None:
        self.assertGreater(repeat_phrase_count("同意这个观点同意这个观点"), 0)
        self.assertEqual(repeat_phrase_count(""), 0)

    def test_classify_risk_returns_low_for_benign_features(self) -> None:
        risk_level, reasons = classify_risk(
            {
                "repetition_count": 0,
                "text_length_ratio": 1.1,
                "speaker_length_imbalance": 0.1,
                "duplicate_removed_count": 0,
                "cleaned_text": "",
                "cleaned_to_separated_ratio": 1.0,
                "method_disagreement_score": 0.1,
            }
        )
        self.assertEqual(risk_level, "low")
        self.assertEqual(reasons, ["low_risk"])

    def test_adjacent_repeat_count_counts_consecutive_duplicates(self) -> None:
        segments = [
            {"text": "你好"},
            {"text": "你好"},
            {"text": "世界"},
        ]
        self.assertEqual(adjacent_repeat_count(segments), 1)

    def test_speaker_lengths_from_segments_returns_per_speaker_lengths(self) -> None:
        segments = [
            {"speaker": "SPEAKER_1", "text": "你好"},
            {"speaker": "SPEAKER_2", "text": "世界"},
            {"speaker": "SPEAKER_1", "text": "再见"},
        ]
        s1_len, s2_len = speaker_lengths_from_segments(segments)
        self.assertEqual(s1_len, 4)
        self.assertEqual(s2_len, 2)

    def test_choose_final_method_keeps_stable_separated_output(self) -> None:
        features = {
            "base_v2_method": "separated_whisper",
            "base_v2_row": {"overlap_level": 0},
            "cleaned_text": "",
            "duplicate_removed_count": 0,
            "cleaned_to_separated_ratio": 1.0,
            "text_length_ratio": 1.1,
        }
        method, action = choose_final_method(features, "low", ["low_risk"])
        self.assertEqual(method, "separated_whisper")
        self.assertIn("stable", action)

    def test_load_case_ids_returns_single_case_or_all(self) -> None:
        self.assertEqual(load_case_ids("LightOverlap"), ["LightOverlap"])
        self.assertIn("NoOverlap", load_case_ids("all"))

    def test_load_table_reads_csv_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "table.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["case_id", "selected_method"])
                writer.writeheader()
                writer.writerow({"case_id": "NoOverlap", "selected_method": "mixed_whisper"})

            rows = load_table(csv_path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["case_id"], "NoOverlap")

    def test_load_map_indexes_rows_by_key_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "rows.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["case_id", "selected_method"])
                writer.writeheader()
                writer.writerow({"case_id": "NoOverlap", "selected_method": "separated_whisper"})

            mapping = load_map(csv_path, "case_id")
            self.assertEqual(mapping["NoOverlap"]["selected_method"], "separated_whisper")


if __name__ == "__main__":
    unittest.main()
