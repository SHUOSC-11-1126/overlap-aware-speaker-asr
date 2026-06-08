from __future__ import annotations

import unittest

from src.frontier_operator_next_action_status_handoff_status_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierOperatorNextActionStatusHandoffStatusBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_uses_combined_state(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "combined_status_handoff_state": "status_handoff_mixed_ready",
                "primary_status_target": "meeteval_compatibility",
            }
        )

        self.assertEqual(rows[0]["combined_status_handoff_state"], "status_handoff_mixed_ready")
        self.assertIn("combined_status_handoff_state=status_handoff_mixed_ready", rows[0]["bridge_note"])
        self.assertIn("meeteval_compatibility", rows[0]["bridge_note"])

    def test_build_bridge_checklist_rows_defaults_status(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows[0]["combined_status_handoff_state"], "status_handoff_unset")


if __name__ == "__main__":
    unittest.main()
