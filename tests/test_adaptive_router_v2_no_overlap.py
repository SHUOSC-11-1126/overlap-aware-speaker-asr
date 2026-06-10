from __future__ import annotations

import unittest

from src.adaptive_router_v2 import choose_method_v2


class AdaptiveRouterV2NoOverlapTest(unittest.TestCase):
    def test_choose_method_v2_prefers_separated_for_long_mixed_transcript(self) -> None:
        method, rule, _ = choose_method_v2(
            overlap_level=0,
            mixed_len=100,
            separated_len=110,
            cleaned_len=105,
            duplicate_removed_count=2,
            runtime_ratio=1.1,
            cleaned_exists=True,
            mixed_segments_count=8,
        )
        self.assertEqual(method, "separated_whisper")
        self.assertIn("long", rule)

    def test_choose_method_v2_falls_back_to_mixed_when_unstable_with_high_duplicates(self) -> None:
        method, rule, unstable = choose_method_v2(
            overlap_level=0,
            mixed_len=100,
            separated_len=160,
            cleaned_len=120,
            duplicate_removed_count=12,
            runtime_ratio=1.1,
            cleaned_exists=True,
            mixed_segments_count=3,
        )
        self.assertTrue(unstable)
        self.assertEqual(method, "mixed_whisper")
        self.assertIn("hallucinations", rule)

    def test_choose_method_v2_chooses_cleaned_when_closer_to_mixed(self) -> None:
        method, rule, _ = choose_method_v2(
            overlap_level=0,
            mixed_len=100,
            separated_len=140,
            cleaned_len=102,
            duplicate_removed_count=2,
            runtime_ratio=1.1,
            cleaned_exists=True,
            mixed_segments_count=3,
        )
        self.assertEqual(method, "separated_whisper_cleaned")
        self.assertIn("cleaned is closer", rule)


if __name__ == "__main__":
    unittest.main()
