from __future__ import annotations

import unittest
from pathlib import Path

from src.generate_synthetic_overlap import choose_pair, tier_gap_sec, tier_overlap_ratio


class GenerateSyntheticOverlapHelpersTest(unittest.TestCase):
    def test_choose_pair_cycles_through_snippet_lists(self) -> None:
        con_files = [Path("con_a.wav"), Path("con_b.wav")]
        pro_files = [Path("pro_x.wav"), Path("pro_y.wav"), Path("pro_z.wav")]
        self.assertEqual(choose_pair(con_files, pro_files, 0), (con_files[0], pro_files[0]))
        self.assertEqual(choose_pair(con_files, pro_files, 1), (con_files[1], pro_files[2]))

    def test_tier_overlap_ratio_returns_zero_for_no_overlap_tier(self) -> None:
        self.assertEqual(tier_overlap_ratio("SyntheticNoOverlap", 0), 0.0)

    def test_tier_overlap_ratio_interpolates_within_range(self) -> None:
        low = tier_overlap_ratio("SyntheticLightOverlap", 0)
        high = tier_overlap_ratio("SyntheticLightOverlap", 4)
        self.assertLess(low, high)
        self.assertGreaterEqual(low, 0.10)
        self.assertLessEqual(high, 0.20)

    def test_tier_gap_sec_returns_zero_when_tier_has_no_gap(self) -> None:
        self.assertEqual(tier_gap_sec("SyntheticLightOverlap", 0), 0.0)

    def test_tier_gap_sec_interpolates_for_no_overlap_tier(self) -> None:
        gap0 = tier_gap_sec("SyntheticNoOverlap", 0)
        gap4 = tier_gap_sec("SyntheticNoOverlap", 4)
        self.assertLess(gap0, gap4)


if __name__ == "__main__":
    unittest.main()
