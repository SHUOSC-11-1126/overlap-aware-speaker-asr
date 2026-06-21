import unittest

from src.generative_audiodepth_reliability_common import leakage_report, sample_rows
from src.rebuild_generative_audiodepth_disjoint_split import split_groups


class GenerativeAudioDepthDisjointSplitTest(unittest.TestCase):
    def test_rebuilt_split_has_no_group_leakage(self):
        splits = split_groups(sample_rows())
        leaks = leakage_report(splits)
        self.assertEqual(leaks["source_utterance_leaks"], 0)
        self.assertEqual(leaks["source_pair_leaks"], 0)
        self.assertEqual(leaks["counterfactual_family_leaks"], 0)
        self.assertEqual(leaks["mixed_wav_leaks"], 0)

    def test_split_is_non_empty(self):
        splits = split_groups(sample_rows())
        self.assertTrue(splits["train"])
        self.assertTrue(splits["validation"])
        self.assertTrue(splits["test"])


if __name__ == "__main__":
    unittest.main()
