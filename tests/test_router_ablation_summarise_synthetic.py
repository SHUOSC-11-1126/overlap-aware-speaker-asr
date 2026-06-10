from __future__ import annotations

import unittest
from typing import Any

from src.router_ablation import STRATEGIES, build_decision_row, summarise_synthetic


def _synthetic_entry(sample_id: str = "syn_001") -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "tier": "SyntheticNoOverlap",
        "overlap_level": 0,
        "mixed_text": "你好世界",
        "separated_text": "你好",
        "cleaned_text": "你好",
        "mixed_segments": [{"text": "你好世界"}],
        "separated_segments": [{"text": "你好"}],
        "cleaned_segments": [{"text": "你好"}],
        "duplicate_removed_count": 0,
        "mixed_runtime_sec": 1.0,
        "separated_runtime_sec": 2.0,
        "cleaned_runtime_sec": 1.5,
        "cleaned_exists": True,
        "cleaned_closer_to_mixed": True,
    }


class RouterAblationSummariseSyntheticTest(unittest.TestCase):
    def test_summarise_synthetic_computes_average_cer_per_strategy(self) -> None:
        entries = [_synthetic_entry("syn_001")]
        decisions = [build_decision_row(entries[0], strategy) for strategy in STRATEGIES]
        cer_lookup = {
            ("syn_001", "mixed_whisper"): 0.25,
            ("syn_001", "separated_whisper"): 0.15,
            ("syn_001", "separated_whisper_cleaned"): 0.18,
        }
        summary = summarise_synthetic(entries, decisions, cer_lookup)
        fixed_mixed = next(row for row in summary if row["strategy"] == "fixed_mixed_whisper")
        oracle = next(row for row in summary if row["strategy"] == "oracle_best")

        self.assertEqual(fixed_mixed["average_cer"], 0.25)
        self.assertEqual(oracle["average_cer"], 0.15)
        self.assertGreaterEqual(fixed_mixed["gap_to_oracle"], 0.0)


if __name__ == "__main__":
    unittest.main()
