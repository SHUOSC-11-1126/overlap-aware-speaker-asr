from __future__ import annotations

import unittest

from src.router_ablation_split import choose_strategy, compute_scope_average, dataset_paths, repetition_count, to_float, to_int


class RouterAblationSplitHelpersTest(unittest.TestCase):
    def test_dataset_paths_returns_synthetic_split_artifacts(self) -> None:
        paths = dataset_paths()
        self.assertIn("manifest", paths)
        self.assertTrue(str(paths["manifest"]).endswith("synthetic_split_manifest.csv"))

    def test_repetition_count_counts_adjacent_duplicates(self) -> None:
        count = repetition_count(
            [{"text": "重复"}, {"text": "重复"}, {"text": "不同"}]
        )
        self.assertEqual(count, 1)

    def test_to_float_and_to_int_parse_numeric_strings(self) -> None:
        self.assertEqual(to_int("2"), 2)
        self.assertEqual(to_float("0.25"), 0.25)
        self.assertEqual(to_int("bad"), 0)
        self.assertIsNone(to_float("bad"))

    def test_choose_strategy_returns_fixed_baselines(self) -> None:
        entry = {
            "overlap_level": 1,
            "mixed_text_length": 100,
            "separated_text_length": 120,
            "cleaned_text_length": 110,
            "repetition_count": 0,
            "duplicate_removed_count": 0,
            "runtime_ratio": 1.0,
            "cleaned_closer_to_mixed": True,
            "mixed_segments_count": 3,
            "text_length_ratio": 1.2,
        }
        method, rule = choose_strategy(entry, "fixed_mixed_whisper")
        self.assertEqual(method, "mixed_whisper")
        self.assertIn("fixed baseline", rule)

    def test_compute_scope_average_averages_oracle_best_cers(self) -> None:
        cer_lookup = {
            ("s1", "mixed_whisper"): 0.3,
            ("s1", "separated_whisper"): 0.1,
        }
        entries = [
            {
                "sample_id": "s1",
                "overlap_level": 0,
                "mixed_text_length": 100,
                "separated_text_length": 110,
                "cleaned_text_length": 0,
                "repetition_count": 0,
                "duplicate_removed_count": 0,
                "runtime_ratio": 1.0,
                "cleaned_closer_to_mixed": False,
                "mixed_segments_count": 3,
                "text_length_ratio": 1.1,
            }
        ]
        average, count = compute_scope_average(cer_lookup, entries, "oracle_best")
        self.assertEqual(average, 0.1)
        self.assertEqual(count, 1)

    def test_choose_strategy_repetition_only_falls_back_to_mixed(self) -> None:
        entry = {
            "overlap_level": 1,
            "mixed_text_length": 100,
            "separated_text_length": 120,
            "cleaned_text_length": 0,
            "repetition_count": 5,
            "duplicate_removed_count": 0,
            "runtime_ratio": 1.0,
            "cleaned_closer_to_mixed": False,
            "mixed_segments_count": 3,
            "text_length_ratio": 1.2,
        }
        method, rule = choose_strategy(entry, "repetition_only")
        self.assertEqual(method, "mixed_whisper")
        self.assertIn("repetition", rule)


if __name__ == "__main__":
    unittest.main()
