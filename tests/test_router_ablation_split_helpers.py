from __future__ import annotations

import unittest

from src.router_ablation_split import dataset_paths, repetition_count, to_float, to_int


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
        self.assertEqual(to_float("bad"), 0.0)


if __name__ == "__main__":
    unittest.main()
