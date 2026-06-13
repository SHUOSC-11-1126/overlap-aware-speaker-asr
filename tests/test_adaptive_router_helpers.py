from __future__ import annotations

import unittest

from src.adaptive_router import compute_strategy_averages, load_case_map, select_method, to_float, to_int
from src.config import load_config


class AdaptiveRouterHelpersTest(unittest.TestCase):
    def test_select_method_uses_overlap_level_rules(self) -> None:
        self.assertEqual(select_method(0)[0], "separated_whisper")
        self.assertEqual(select_method(1)[0], "mixed_whisper")
        self.assertEqual(select_method(3)[0], "separated_whisper")

    def test_to_int_and_to_float_parse_numeric_strings(self) -> None:
        self.assertEqual(to_int("12"), 12)
        self.assertEqual(to_float("0.5"), 0.5)

    def test_to_int_and_to_float_return_defaults_for_invalid_input(self) -> None:
        self.assertEqual(to_int("bad"), 0)
        self.assertIsNone(to_float("bad"))

    def test_load_case_map_indexes_cases_by_id(self) -> None:
        config = load_config()
        case_map = load_case_map(config)
        self.assertIn("NoOverlap", case_map)
        self.assertEqual(case_map["NoOverlap"]["overlap_level"], 0)

    def test_compute_strategy_averages_builds_oracle_and_rule_router_rows(self) -> None:
        cer_lookup = {
            ("NoOverlap", "mixed_whisper"): 0.2,
            ("NoOverlap", "separated_whisper"): 0.05,
            ("NoOverlap", "separated_whisper_cleaned"): 0.09,
        }
        decisions = [{"case_id": "NoOverlap", "selected_method": "separated_whisper"}]
        performance = compute_strategy_averages(cer_lookup, decisions)
        by_strategy = {row["strategy"]: row["average_cer"] for row in performance}
        self.assertEqual(by_strategy["oracle_best"], 0.05)
        self.assertEqual(by_strategy["rule_router"], 0.05)


if __name__ == "__main__":
    unittest.main()
