from __future__ import annotations

import unittest

from src.adaptive_router_v2 import choose_method_v2, is_unstable


class AdaptiveRouterV2StabilityTest(unittest.TestCase):
    def test_is_unstable_flags_length_inflation(self) -> None:
        self.assertTrue(is_unstable(mixed_len=100, separated_len=150, duplicate_removed_count=0, runtime_ratio=1.0))

    def test_is_unstable_flags_high_duplicate_removal(self) -> None:
        self.assertTrue(is_unstable(mixed_len=100, separated_len=100, duplicate_removed_count=10, runtime_ratio=1.0))

    def test_is_unstable_is_false_for_balanced_outputs(self) -> None:
        self.assertFalse(is_unstable(mixed_len=100, separated_len=110, duplicate_removed_count=2, runtime_ratio=1.2))


class AdaptiveRouterV2NoOverlapDecisionTest(unittest.TestCase):
    def test_choose_method_v2_prefers_mixed_for_short_no_overlap(self) -> None:
        method, rule, _ = choose_method_v2(
            overlap_level=0,
            mixed_len=80,
            separated_len=90,
            cleaned_len=0,
            duplicate_removed_count=0,
            runtime_ratio=1.0,
            cleaned_exists=False,
            mixed_segments_count=3,
        )
        self.assertEqual(method, "mixed_whisper")
        self.assertIn("short transcript", rule)

    def test_choose_method_v2_prefers_separated_for_long_no_overlap(self) -> None:
        method, _, _ = choose_method_v2(
            overlap_level=0,
            mixed_len=200,
            separated_len=210,
            cleaned_len=0,
            duplicate_removed_count=0,
            runtime_ratio=1.0,
            cleaned_exists=False,
            mixed_segments_count=8,
        )
        self.assertEqual(method, "separated_whisper")


class AdaptiveRouterV2OverlapLevelDecisionTest(unittest.TestCase):
    def test_choose_method_v2_prefers_mixed_for_light_overlap(self) -> None:
        method, rule, _ = choose_method_v2(
            overlap_level=1,
            mixed_len=100,
            separated_len=100,
            cleaned_len=0,
            duplicate_removed_count=0,
            runtime_ratio=1.0,
            cleaned_exists=False,
            mixed_segments_count=4,
        )
        self.assertEqual(method, "mixed_whisper")
        self.assertIn("overlap_level in [1,2]", rule)

    def test_choose_method_v2_prefers_separated_for_heavy_overlap(self) -> None:
        method, rule, _ = choose_method_v2(
            overlap_level=3,
            mixed_len=100,
            separated_len=100,
            cleaned_len=0,
            duplicate_removed_count=0,
            runtime_ratio=1.0,
            cleaned_exists=False,
            mixed_segments_count=4,
        )
        self.assertEqual(method, "separated_whisper")
        self.assertIn("overlap_level>=3", rule)


if __name__ == "__main__":
    unittest.main()
