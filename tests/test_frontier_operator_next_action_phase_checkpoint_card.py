from __future__ import annotations

import unittest

from src.frontier_operator_next_action_phase_checkpoint_card import build_phase_checkpoint_row


class FrontierOperatorNextActionPhaseCheckpointCardTest(unittest.TestCase):
    def test_build_phase_checkpoint_row_uses_runbook_completion_signal(self) -> None:
        row = build_phase_checkpoint_row(
            {
                "recommended_frontier": "meeteval_compatibility",
                "recommended_action": "Fill the official receipt with real evidence.",
                "completion_signal": "ready_lane verification is complete and the target artifact results/tables/meeteval_cpwer_execution_receipt.json is ready to open",
            }
        )

        self.assertEqual(row["checkpoint_frontier"], "meeteval_compatibility")
        self.assertIn("meeteval_cpwer_execution_receipt.json", row["completion_signal"])


if __name__ == "__main__":
    unittest.main()
