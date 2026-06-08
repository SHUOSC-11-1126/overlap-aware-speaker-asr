from __future__ import annotations

import unittest

from src.frontier_operator_next_action_frontier_bridge_checklist import build_bridge_checklist_rows


class FrontierOperatorNextActionFrontierBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_runbook_card(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "runbook_frontier": "meeteval_compatibility",
                "frontier_queue_head": "meeteval_compatibility",
                "bridge_note": "Aligned queue heads.",
            }
        )

        self.assertIn("runbook_card", rows[0]["receipt_target"])
        self.assertEqual(rows[0]["bridge_note"], "Aligned queue heads.")

    def test_build_bridge_checklist_rows_returns_empty_for_no_bridge(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
