from __future__ import annotations

import unittest

from src.adaptive_router_v2 import choose_method_v2, is_unstable, load_case_map, read_csv_rows, read_json
from src.config import PROJECT_ROOT, load_config


class AdaptiveRouterV2LoadHelpersTest(unittest.TestCase):
    def test_load_case_map_indexes_audio_cases_by_id(self) -> None:
        case_map = load_case_map(load_config())
        self.assertIn("NoOverlap", case_map)
        self.assertEqual(case_map["NoOverlap"]["overlap_level"], 0)

    def test_read_csv_rows_raises_for_missing_table(self) -> None:
        missing = PROJECT_ROOT / "results" / "tables" / "__missing_router_table__.csv"
        with self.assertRaises(FileNotFoundError):
            read_csv_rows(missing)

    def test_read_json_raises_for_missing_file(self) -> None:
        missing = PROJECT_ROOT / "results" / "tables" / "__missing_router__.json"
        with self.assertRaises(FileNotFoundError):
            read_json(missing)

    def test_is_unstable_flags_high_runtime_ratio(self) -> None:
        self.assertTrue(is_unstable(mixed_len=100, separated_len=110, duplicate_removed_count=0, runtime_ratio=2.0))

    def test_choose_method_v2_defaults_to_mixed_for_short_no_overlap(self) -> None:
        method, rule, _ = choose_method_v2(
            overlap_level=0,
            mixed_len=100,
            separated_len=130,
            cleaned_len=120,
            duplicate_removed_count=6,
            runtime_ratio=1.1,
            cleaned_exists=True,
            mixed_segments_count=3,
        )
        self.assertEqual(method, "mixed_whisper")
        self.assertIn("short transcript", rule)


if __name__ == "__main__":
    unittest.main()
