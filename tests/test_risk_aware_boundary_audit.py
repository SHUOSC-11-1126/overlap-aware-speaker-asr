from __future__ import annotations

import unittest

from src.risk_aware_boundary_audit import build_audit_rows, build_summary_rows


class RiskAwareBoundaryAuditTest(unittest.TestCase):
    def test_build_audit_rows_flags_risk_override(self) -> None:
        risk_rows = [
            {
                "case_id": "HeavyOverlap",
                "base_router_method": "separated_whisper",
                "final_selected_method": "separated_whisper_cleaned",
                "risk_level": "medium",
                "recommended_action": "repair separated output",
            }
        ]
        cer_by_case = {
            "HeavyOverlap": {
                "mixed_whisper": 0.39,
                "separated_whisper": 0.11,
                "separated_whisper_cleaned": 0.15,
            }
        }
        rows = build_audit_rows(risk_rows, cer_by_case)
        self.assertTrue(rows[0]["risk_layer_changed_method"])
        self.assertTrue(rows[0]["selector_aligns_with_phase"])

    def test_build_summary_rows_includes_override_rate(self) -> None:
        rows = [
            {"selector_matches_oracle": True, "selector_aligns_with_phase": True, "selector_regret_cer": 0.0, "risk_layer_changed_method": True},
            {"selector_matches_oracle": True, "selector_aligns_with_phase": True, "selector_regret_cer": 0.0, "risk_layer_changed_method": False},
        ]
        summary = build_summary_rows(rows)
        metrics = {row["metric"]: row["value"] for row in summary}
        self.assertEqual(metrics["risk_layer_override_rate"], "0.5")


if __name__ == "__main__":
    unittest.main()
