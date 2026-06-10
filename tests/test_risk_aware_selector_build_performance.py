from __future__ import annotations

import unittest
from typing import Any

from src.risk_aware_selector import build_performance


def _selection_row(case_id: str, base_method: str, final_method: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "base_router_method": base_method,
        "final_selected_method": final_method,
    }


class RiskAwareSelectorBuildPerformanceTest(unittest.TestCase):
    def test_build_performance_averages_fixed_strategy_cer(self) -> None:
        rows = [
            _selection_row("NoOverlap", "separated_whisper", "separated_whisper"),
            _selection_row("LightOverlap", "mixed_whisper", "mixed_whisper"),
        ]
        cer_lookup = {
            ("NoOverlap", "mixed_whisper"): 0.20,
            ("NoOverlap", "separated_whisper"): 0.10,
            ("LightOverlap", "mixed_whisper"): 0.30,
            ("LightOverlap", "separated_whisper"): 0.40,
        }
        performance = build_performance(rows, cer_lookup)
        fixed_mixed = next(row for row in performance if row["strategy"] == "fixed_mixed_whisper")
        fixed_separated = next(row for row in performance if row["strategy"] == "fixed_separated_whisper")
        oracle = next(row for row in performance if row["strategy"] == "oracle_best")

        self.assertEqual(fixed_mixed["average_cer"], 0.25)
        self.assertEqual(fixed_separated["average_cer"], 0.25)
        self.assertEqual(oracle["average_cer"], 0.20)

    def test_build_performance_uses_final_selected_method_for_risk_aware_strategy(self) -> None:
        rows = [_selection_row("NoOverlap", "separated_whisper", "mixed_whisper")]
        cer_lookup = {
            ("NoOverlap", "mixed_whisper"): 0.18,
            ("NoOverlap", "separated_whisper"): 0.12,
        }
        performance = build_performance(rows, cer_lookup)
        risk_aware = next(row for row in performance if row["strategy"] == "risk_aware_selector")
        self.assertEqual(risk_aware["average_cer"], 0.18)


if __name__ == "__main__":
    unittest.main()
