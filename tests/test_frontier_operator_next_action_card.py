from __future__ import annotations

import unittest

from src.frontier_operator_next_action_card import build_action_rows, build_summary_row


class FrontierOperatorNextActionCardTest(unittest.TestCase):
    def test_build_action_rows_emits_ready_then_blocked_lane(self) -> None:
        board_rows = [
            {
                "frontier_name": "external_validation",
                "go_no_go_state": "no_go",
                "current_state": "blocked_by_license_confirmation",
                "recommended_next_action": "Record and write back the license confirmation decision before any external staging attempt.",
                "evidence_artifact": "results/figures/external_validation_go_no_go_summary.md",
                "primary_boundary": "license_confirmation_pending",
            },
            {
                "frontier_name": "meeteval_compatibility",
                "go_no_go_state": "go",
                "current_state": "receipt_ready_to_fill",
                "recommended_next_action": "If execution starts, use character-spaced cpWER and fill the official receipt with real evidence.",
                "evidence_artifact": "results/figures/meeteval_cpwer_tokenization_gain_scorecard_summary.md",
                "primary_boundary": "official_benchmark_claims_still_blocked_until_receipt_fill",
            },
        ]
        summary_row = {
            "highest_priority_ready_frontier": "meeteval_compatibility",
            "highest_priority_blocked_frontier": "external_validation",
            "coordination_state": "mixed_ready_state",
        }

        rows = build_action_rows(board_rows, summary_row)

        self.assertEqual([row["action_lane"] for row in rows], ["ready_lane", "blocked_lane"])
        self.assertEqual(rows[0]["frontier_name"], "meeteval_compatibility")
        self.assertEqual(rows[1]["frontier_name"], "external_validation")

    def test_build_summary_row_records_operator_sequence(self) -> None:
        rows = [
            {"action_lane": "ready_lane", "frontier_name": "meeteval_compatibility"},
            {"action_lane": "blocked_lane", "frontier_name": "external_validation"},
        ]
        go_no_go_summary = {
            "coordination_state": "mixed_ready_state",
            "highest_priority_ready_frontier": "meeteval_compatibility",
            "highest_priority_blocked_frontier": "external_validation",
        }

        row = build_summary_row(rows, go_no_go_summary)

        self.assertEqual(row["ready_frontier"], "meeteval_compatibility")
        self.assertEqual(row["blocked_frontier"], "external_validation")
        self.assertEqual(row["operator_sequence"], "ready_lane:meeteval_compatibility -> blocked_lane:external_validation")


if __name__ == "__main__":
    unittest.main()
