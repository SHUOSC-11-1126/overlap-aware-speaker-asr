from __future__ import annotations

import unittest

from src.adaptive_router_v2 import choose_method_v2, is_unstable, to_float, to_int


class AdaptiveRouterV2HelpersTest(unittest.TestCase):
    def test_is_unstable_flags_length_ratio_and_duplicates(self) -> None:
        self.assertTrue(is_unstable(mixed_len=100, separated_len=150, duplicate_removed_count=0, runtime_ratio=1.0))
        self.assertTrue(is_unstable(mixed_len=100, separated_len=110, duplicate_removed_count=10, runtime_ratio=1.0))
        self.assertFalse(is_unstable(mixed_len=100, separated_len=110, duplicate_removed_count=2, runtime_ratio=1.0))

    def test_choose_method_v2_prefers_mixed_for_light_overlap(self) -> None:
        method, rule, unstable = choose_method_v2(
            overlap_level=1,
            mixed_len=100,
            separated_len=120,
            cleaned_len=110,
            duplicate_removed_count=2,
            runtime_ratio=1.1,
            cleaned_exists=True,
            mixed_segments_count=3,
        )
        self.assertEqual(method, "mixed_whisper")
        self.assertIn("overlap_level in [1,2]", rule)

    def test_choose_method_v2_prefers_separated_for_heavy_overlap(self) -> None:
        method, _, _ = choose_method_v2(
            overlap_level=3,
            mixed_len=100,
            separated_len=120,
            cleaned_len=110,
            duplicate_removed_count=2,
            runtime_ratio=1.1,
            cleaned_exists=True,
            mixed_segments_count=3,
        )
        self.assertEqual(method, "separated_whisper")

    def test_to_int_and_to_float_parse_numeric_strings(self) -> None:
        self.assertEqual(to_int("4"), 4)
        self.assertEqual(to_float("0.75"), 0.75)
        self.assertEqual(to_int("bad"), 0)
        self.assertIsNone(to_float("bad"))


if __name__ == "__main__":
    unittest.main()
