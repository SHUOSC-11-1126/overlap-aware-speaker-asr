from __future__ import annotations

import unittest

from src.frontier_operator_next_action_status_handoff_bridge_checklist import build_bridge_checklist_rows


class FrontierOperatorNextActionStatusHandoffBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_uses_lane_and_status(self) -> None:
        rows = build_bridge_checklist_rows(
            [
                {
                    "handoff_order": "1",
                    "action_lane": "ready_lane",
                    "frontier_name": "meeteval_compatibility",
                    "combined_operator_status": "operator_status_mixed_ready",
                    "expected_outputs": "results/tables/meeteval_cpwer_execution_receipt.json",
                },
                {
                    "handoff_order": "2",
                    "action_lane": "blocked_lane",
                    "frontier_name": "external_validation",
                    "combined_operator_status": "operator_status_mixed_ready",
                    "expected_outputs": "results/tables/external_validation_license_confirmation_receipt_bridge.json",
                },
            ]
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["action_lane"], "ready_lane")
        self.assertEqual(rows[1]["action_lane"], "blocked_lane")
        self.assertIn("operator_status_mixed_ready", rows[0]["bridge_note"])

    def test_build_bridge_checklist_rows_returns_empty_when_no_handoff_rows(self) -> None:
        rows = build_bridge_checklist_rows([])

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
