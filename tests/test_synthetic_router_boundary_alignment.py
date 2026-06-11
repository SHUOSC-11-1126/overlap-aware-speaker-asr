from __future__ import annotations

import unittest

from src.synthetic_router_boundary_alignment import build_alignment_rows, build_summary_rows


class SyntheticRouterBoundaryAlignmentTest(unittest.TestCase):
    def test_build_alignment_rows_uses_v2_decision(self) -> None:
        cer_rows = [
            {
                "sample_id": "SyntheticLightOverlap_test_01",
                "split": "test",
                "tier": "SyntheticLightOverlap",
                "method": "mixed_whisper",
                "cer": "0.1",
            },
            {
                "sample_id": "SyntheticLightOverlap_test_01",
                "split": "test",
                "tier": "SyntheticLightOverlap",
                "method": "separated_whisper",
                "cer": "0.3",
            },
            {
                "sample_id": "SyntheticLightOverlap_test_01",
                "split": "test",
                "tier": "SyntheticLightOverlap",
                "method": "separated_whisper_cleaned",
                "cer": "0.2",
            },
        ]
        decision_rows = [
            {
                "sample_id": "SyntheticLightOverlap_test_01",
                "strategy": "v2_full_features",
                "selected_method": "mixed_whisper",
                "decision_rule": "overlap_level in [1,2]",
            }
        ]
        manifest = {
            "SyntheticLightOverlap_test_01": {"overlap_ratio": "0.15", "split": "test", "tier": "SyntheticLightOverlap"}
        }
        rows = build_alignment_rows(cer_rows, decision_rows, manifest)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["router_matches_oracle"])
        self.assertTrue(rows[0]["router_aligns_with_phase"])

    def test_build_summary_rows_includes_test_scope(self) -> None:
        rows = [
            {
                "split": "test",
                "router_matches_oracle": True,
                "router_aligns_with_phase": True,
                "router_regret_cer": 0.0,
            },
            {
                "split": "dev",
                "router_matches_oracle": False,
                "router_aligns_with_phase": False,
                "router_regret_cer": 0.2,
            },
        ]
        summary = build_summary_rows(rows)
        scopes = {row["scope"] for row in summary}
        self.assertIn("test", scopes)
        self.assertIn("ALL", scopes)


if __name__ == "__main__":
    unittest.main()
