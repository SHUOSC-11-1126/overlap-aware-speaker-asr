from __future__ import annotations

import unittest

from src.adaptive_router import build_decisions
from src.config import load_config


class AdaptiveRouterBuildDecisionsTest(unittest.TestCase):
    def test_build_decisions_returns_one_row_per_configured_case(self) -> None:
        config = load_config()
        mixed_rows = {
            "NoOverlap": {"segments_count": 3, "text_length": 100, "runtime_sec": 1.0},
        }
        separated_rows = {
            "NoOverlap": {"merged_segments_count": 4, "full_text_length": 90, "runtime_sec_total": 2.0},
        }
        cleaned_rows = {
            "NoOverlap": {"removed_count": 1},
        }
        decisions = build_decisions(config, mixed_rows, separated_rows, cleaned_rows)
        self.assertEqual(len(decisions), 5)
        no_overlap = next(row for row in decisions if row["case_id"] == "NoOverlap")
        self.assertIn(no_overlap["selected_method"], {"mixed_whisper", "separated_whisper"})
        self.assertEqual(no_overlap["duplicate_removed_count"], 1)


if __name__ == "__main__":
    unittest.main()
