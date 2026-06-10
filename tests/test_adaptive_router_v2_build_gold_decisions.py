from __future__ import annotations

import unittest
from typing import Any

from src.adaptive_router_v2 import build_gold_decisions
from src.config import load_config


def _benchmark_row(**overrides: Any) -> dict[str, Any]:
    base = {
        "segments_count": 3,
        "text_length": 100,
        "runtime_sec": 1.0,
        "merged_segments_count": 4,
        "full_text_length": 90,
        "runtime_sec_total": 2.0,
    }
    base.update(overrides)
    return base


def _cleaned_row(**overrides: Any) -> dict[str, Any]:
    base = {
        "cleaned_segments": [{"text": "清理"}],
        "cleaned_full_text": "清理文本",
        "removed_count": 1,
    }
    base.update(overrides)
    return base


class AdaptiveRouterV2BuildGoldDecisionsTest(unittest.TestCase):
    def test_build_gold_decisions_returns_row_per_config_case(self) -> None:
        config = load_config()
        mixed = {"NoOverlap": _benchmark_row()}
        separated = {"NoOverlap": _benchmark_row()}
        cleaned = {"NoOverlap": _cleaned_row()}
        decisions = build_gold_decisions(config, mixed, separated, cleaned)
        case_ids = {row["case_id"] for row in decisions}
        self.assertIn("NoOverlap", case_ids)
        self.assertGreaterEqual(len(decisions), 5)

    def test_build_gold_decisions_marks_light_overlap_as_mixed_whisper(self) -> None:
        config = load_config()
        mixed = {"LightOverlap": _benchmark_row()}
        separated = {"LightOverlap": _benchmark_row(text_length=100, full_text_length=120)}
        cleaned = {"LightOverlap": _cleaned_row(cleaned_full_text="混合接近", removed_count=1)}
        decisions = build_gold_decisions(config, mixed, separated, cleaned)
        light = next(row for row in decisions if row["case_id"] == "LightOverlap")
        self.assertEqual(light["selected_method"], "mixed_whisper")
        self.assertIn("overlap_level in [1,2]", light["decision_rule"])


if __name__ == "__main__":
    unittest.main()
