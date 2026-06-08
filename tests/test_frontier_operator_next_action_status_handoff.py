from __future__ import annotations

import unittest

from src.frontier_operator_next_action_status_handoff import build_handoff_rows


class FrontierOperatorNextActionStatusHandoffTest(unittest.TestCase):
    def test_build_handoff_rows_uses_ready_and_blocked_lanes(self) -> None:
        rows = build_handoff_rows(
            {"combined_operator_status": "operator_status_mixed_ready"},
            [
                {
                    "action_lane": "ready_lane",
                    "frontier_name": "meeteval_compatibility",
                    "operator_action": "Fill the execution receipt with real evidence.",
                    "target_artifact": "results/tables/meeteval_cpwer_execution_receipt.json",
                },
                {
                    "action_lane": "blocked_lane",
                    "frontier_name": "external_validation",
                    "operator_action": "Record the license confirmation decision first.",
                    "target_artifact": "results/tables/external_validation_license_confirmation_receipt_bridge.json",
                },
            ],
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["frontier_name"], "meeteval_compatibility")
        self.assertEqual(rows[1]["frontier_name"], "external_validation")
        self.assertEqual(rows[0]["combined_operator_status"], "operator_status_mixed_ready")
        self.assertIn("license confirmation", rows[1]["recommended_action"])

    def test_build_handoff_rows_returns_empty_without_card_rows(self) -> None:
        rows = build_handoff_rows({}, [])

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
