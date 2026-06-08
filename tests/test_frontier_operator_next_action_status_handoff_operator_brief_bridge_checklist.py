from __future__ import annotations

import unittest

from src.frontier_operator_next_action_status_handoff_operator_brief_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierOperatorNextActionStatusHandoffOperatorBriefBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_runbook_gate(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "reentry_frontier": "meeteval_compatibility",
                "prerequisite_artifact": "results/figures/frontier_operator_next_action_status_handoff_operator_brief.md",
                "receipt_target": "results/figures/frontier_operator_next_action_status_handoff_runbook_card.md",
                "bridge_note": "Open the operator brief first.",
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertIn("status_handoff_runbook_card.md", rows[0]["next_gate"])

    def test_build_bridge_checklist_rows_returns_empty_without_bridge(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
