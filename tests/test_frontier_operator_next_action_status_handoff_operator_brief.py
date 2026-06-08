from __future__ import annotations

import unittest

from src.frontier_operator_next_action_status_handoff_operator_brief import build_operator_brief_row


class FrontierOperatorNextActionStatusHandoffOperatorBriefTest(unittest.TestCase):
    def test_build_operator_brief_row_summarizes_ready_and_blocked_lanes(self) -> None:
        row = build_operator_brief_row(
            {
                "queue_status": "queue_complete",
                "ready_lane_count": "1",
                "blocked_lane_count": "1",
            },
            [
                {
                    "action_lane": "ready_lane",
                    "frontier_name": "meeteval_compatibility",
                    "recommended_action": "Fill the official receipt with real evidence.",
                    "expected_outputs": "results/tables/meeteval_cpwer_execution_receipt.json",
                },
                {
                    "action_lane": "blocked_lane",
                    "frontier_name": "external_validation",
                    "recommended_action": "Record the license confirmation decision.",
                    "expected_outputs": "results/tables/external_validation_license_confirmation_receipt_bridge.json",
                },
            ],
        )

        self.assertEqual(row["ready_frontier"], "meeteval_compatibility")
        self.assertIn("Fill the official receipt", row["ready_action"])
        self.assertEqual(row["blocked_frontier"], "external_validation")
        self.assertIn("queue_complete", row["operator_urgency"])

    def test_build_operator_brief_row_returns_empty_when_no_rows(self) -> None:
        row = build_operator_brief_row({}, [])

        self.assertEqual(row, {})


if __name__ == "__main__":
    unittest.main()
