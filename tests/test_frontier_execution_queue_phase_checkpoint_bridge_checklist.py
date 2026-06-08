from __future__ import annotations

import unittest

from src.frontier_execution_queue_phase_checkpoint_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierExecutionQueuePhaseCheckpointBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_links_checkpoint_to_milestone(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "checkpoint_frontier": "meeteval_compatibility",
                "completion_signal": (
                    "execution queue verification is complete and the target artifact "
                    "results/tables/meeteval_cpwer_execution_receipt.json is ready to open"
                ),
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["checkpoint_frontier"], "meeteval_compatibility")
        self.assertIn("frontier_execution_queue_milestone_card.md", rows[0]["receipt_target"])
        self.assertIn("meeteval_cpwer_execution_receipt.json", rows[0]["bridge_note"])

    def test_build_bridge_checklist_rows_returns_empty_without_checkpoint(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
