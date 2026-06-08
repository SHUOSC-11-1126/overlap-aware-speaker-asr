from __future__ import annotations

import unittest

from src.frontier_operator_next_action_status_handoff_phase_checkpoint_card import build_phase_checkpoint_row


class FrontierOperatorNextActionStatusHandoffPhaseCheckpointCardTest(unittest.TestCase):
    def test_build_phase_checkpoint_row_uses_runbook_completion_signal(self) -> None:
        row = build_phase_checkpoint_row(
            {
                "recommended_frontier": "meeteval_compatibility",
                "recommended_action": "Fill the official receipt with real evidence.",
                "completion_signal": "ready_lane verification is complete and the target artifact is ready to open",
            }
        )

        self.assertEqual(row["checkpoint_frontier"], "meeteval_compatibility")
        self.assertIn("Fill the official receipt", row["checkpoint_action"])
        self.assertIn("ready_lane verification", row["completion_signal"])

    def test_build_phase_checkpoint_row_returns_empty_without_runbook(self) -> None:
        row = build_phase_checkpoint_row({})

        self.assertEqual(row, {})


if __name__ == "__main__":
    unittest.main()
