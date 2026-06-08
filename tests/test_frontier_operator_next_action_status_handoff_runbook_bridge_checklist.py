from __future__ import annotations

import unittest

from src.frontier_operator_next_action_status_handoff_runbook_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierOperatorNextActionStatusHandoffRunbookBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_links_runbook_to_phase_checkpoint(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "recommended_frontier": "meeteval_compatibility",
                "runbook_note": "Start with meeteval_compatibility.",
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertIn("status_handoff_phase_checkpoint_card.md", rows[0]["receipt_target"])

    def test_build_bridge_checklist_rows_returns_empty_without_runbook(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
