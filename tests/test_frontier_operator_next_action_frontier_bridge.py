from __future__ import annotations

import unittest

from src.frontier_operator_next_action_frontier_bridge import build_frontier_bridge_row


class FrontierOperatorNextActionFrontierBridgeTest(unittest.TestCase):
    def test_build_frontier_bridge_row_aligns_runbook_and_queue_head(self) -> None:
        row = build_frontier_bridge_row(
            {"recommended_frontier": "meeteval_compatibility"},
            {"highest_priority_ready_frontier": "meeteval_compatibility"},
        )

        self.assertEqual(row["runbook_frontier"], "meeteval_compatibility")
        self.assertEqual(row["frontier_queue_head"], "meeteval_compatibility")
        self.assertIn("aligns", row["bridge_reason"])

    def test_build_frontier_bridge_row_returns_empty_without_runbook(self) -> None:
        row = build_frontier_bridge_row({}, {})

        self.assertEqual(row, {})


if __name__ == "__main__":
    unittest.main()
