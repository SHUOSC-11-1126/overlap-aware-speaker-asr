from __future__ import annotations

import unittest

from src.frontier_execution_receipt_queue_writeback_open_card_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierExecutionReceiptQueueWritebackOpenCardBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_maps_open_card_to_receipt(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "frontier_name": "speaker_profile",
                "writeback_status": "awaiting_writeback",
                "receipt_target": "results/tables/speaker_profile_embedding_trial_execution_receipt.json",
            }
        )

        self.assertEqual(rows[0]["frontier_name"], "speaker_profile")
        self.assertEqual(
            rows[0]["receipt_target"],
            "results/tables/speaker_profile_embedding_trial_execution_receipt.json",
        )
        self.assertIn("speaker_profile_embedding_trial_execution_receipt.json", rows[0]["next_gate"])


if __name__ == "__main__":
    unittest.main()
