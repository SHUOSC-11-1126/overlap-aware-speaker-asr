from __future__ import annotations

import unittest
from typing import Any

from src.router_ablation import build_decision_row


def _sample_entry() -> dict[str, Any]:
    return {
        "case_id": "NoOverlap",
        "overlap_level": 0,
        "mixed_text": "你好世界",
        "separated_text": "你好",
        "cleaned_text": "",
        "mixed_segments": [{"text": "你好世界"}],
        "separated_segments": [{"text": "你好"}],
        "cleaned_segments": [],
        "duplicate_removed_count": 0,
        "mixed_runtime_sec": 1.0,
        "separated_runtime_sec": 2.0,
        "cleaned_runtime_sec": 0.0,
        "cleaned_exists": False,
        "cleaned_closer_to_mixed": False,
    }


class RouterAblationBuildDecisionRowTest(unittest.TestCase):
    def test_build_decision_row_includes_strategy_metadata(self) -> None:
        row = build_decision_row(_sample_entry(), "fixed_mixed_whisper")
        self.assertEqual(row["case_id"], "NoOverlap")
        self.assertEqual(row["strategy"], "fixed_mixed_whisper")
        self.assertEqual(row["selected_method"], "mixed_whisper")
        self.assertIn("Fixed baseline", row["notes"])

    def test_build_decision_row_computes_text_length_ratio(self) -> None:
        row = build_decision_row(_sample_entry(), "oracle_best")
        self.assertGreater(row["text_length_ratio"], 0.0)


if __name__ == "__main__":
    unittest.main()
