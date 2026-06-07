from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_phase_checkpoint_card import (
    build_phase_checkpoint_row,
)


class FrontierExecutionReceiptFillExecutionPhaseCheckpointCardTest(unittest.TestCase):
    def test_build_phase_checkpoint_row_uses_runbook_completion_signal(self) -> None:
        row = build_phase_checkpoint_row(
            {
                "recommended_frontier": "meeteval_compatibility",
                "recommended_action": "Execute the real frontier run.",
                "completion_signal": "execution_status is no longer template_only",
            }
        )

        self.assertEqual(row["checkpoint_frontier"], "meeteval_compatibility")
        self.assertIn("template_only", row["completion_signal"])


if __name__ == "__main__":
    unittest.main()
