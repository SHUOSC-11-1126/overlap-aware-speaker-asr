from __future__ import annotations

import unittest
from typing import Any

from src.evaluate_synthetic_routing import STRATEGIES, build_performance


def _manifest_row(sample_id: str, tier: str = "SyntheticNoOverlap", split: str = "train") -> dict[str, Any]:
    return {"sample_id": sample_id, "tier": tier, "split": split}


def _decision(sample_id: str, strategy: str, method: str) -> dict[str, Any]:
    return {"sample_id": sample_id, "strategy": strategy, "selected_method": method}


class EvaluateSyntheticRoutingBuildPerformanceTest(unittest.TestCase):
    def test_build_performance_emits_scope_strategy_rows(self) -> None:
        manifest = [_manifest_row("s1"), _manifest_row("s2", tier="SyntheticLightOverlap", split="val")]
        decisions = [
            _decision("s1", strategy, "mixed_whisper" if strategy == "fixed_mixed_whisper" else "separated_whisper")
            for strategy in STRATEGIES
        ] + [
            _decision("s2", strategy, "mixed_whisper")
            for strategy in STRATEGIES
        ]
        cer_lookup = {
            ("s1", "mixed_whisper"): 0.20,
            ("s1", "separated_whisper"): 0.10,
            ("s2", "mixed_whisper"): 0.30,
        }
        performance = build_performance(manifest, decisions, cer_lookup)
        scopes = {row["scope"] for row in performance}
        self.assertIn("ALL", scopes)
        self.assertIn("SyntheticNoOverlap", scopes)
        self.assertTrue(all(row["strategy"] in STRATEGIES for row in performance))


if __name__ == "__main__":
    unittest.main()
