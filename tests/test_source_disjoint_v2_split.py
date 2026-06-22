import unittest

from src.source_disjoint_v2_common import build_source_disjoint_benchmark_v2, load_joined_rows, split_leakage


class SourceDisjointV2SplitTest(unittest.TestCase):
    def test_split_has_no_source_leakage(self):
        build_source_disjoint_benchmark_v2()
        leak = split_leakage(load_joined_rows())
        self.assertEqual(leak["source_utterance_leaks"], 0)
        self.assertEqual(leak["source_pair_leaks"], 0)

    def test_strict_splits_are_non_empty(self):
        build_source_disjoint_benchmark_v2()
        rows = load_joined_rows()
        for split in ["train", "validation", "test"]:
            self.assertTrue([row for row in rows if row["source_disjoint_split"] == split])


if __name__ == "__main__":
    unittest.main()
