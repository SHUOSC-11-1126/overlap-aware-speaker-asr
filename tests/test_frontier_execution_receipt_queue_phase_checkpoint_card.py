from __future__ import annotations

import unittest

from src.frontier_execution_receipt_queue_phase_checkpoint_card import build_phase_checkpoint_row


class FrontierExecutionReceiptQueuePhaseCheckpointCardTest(unittest.TestCase):
    def test_build_phase_checkpoint_row_uses_runbook_completion_signal(self) -> None:
        row = build_phase_checkpoint_row(
            {
                "recommended_frontier": "meeteval_compatibility",
                "recommended_action": (
                    "Update execution_status in results/tables/meeteval_cpwer_execution_receipt.json "
                    "after a real frontier run and bridge verification."
                ),
                "completion_signal": (
                    "receipt queue verification is complete and the target receipt "
                    "results/tables/meeteval_cpwer_execution_receipt.json is ready to update"
                ),
            }
        )

        self.assertEqual(row["checkpoint_frontier"], "meeteval_compatibility")
        self.assertIn("Update execution_status", row["checkpoint_action"])
        self.assertIn("meeteval_cpwer_execution_receipt.json", row["completion_signal"])

    def test_build_phase_checkpoint_row_returns_empty_without_runbook(self) -> None:
        row = build_phase_checkpoint_row({})

        self.assertEqual(row, {})


if __name__ == "__main__":
    unittest.main()
