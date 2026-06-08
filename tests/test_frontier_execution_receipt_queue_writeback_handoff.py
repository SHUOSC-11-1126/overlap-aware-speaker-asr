from __future__ import annotations

import unittest

from src.frontier_execution_receipt_queue_writeback_handoff import build_handoff_rows


class FrontierExecutionReceiptQueueWritebackHandoffTest(unittest.TestCase):
    def test_build_handoff_rows_recommends_execute_when_awaiting(self) -> None:
        rows = build_handoff_rows(
            [
                {
                    "frontier_name": "meeteval_compatibility",
                    "writeback_status": "writeback_complete",
                },
                {
                    "frontier_name": "speaker_profile",
                    "writeback_status": "awaiting_writeback",
                },
                {
                    "frontier_name": "external_validation",
                    "writeback_status": "awaiting_writeback",
                },
            ]
        )

        self.assertEqual(rows[1]["frontier_name"], "speaker_profile")
        self.assertIn("Execute the real speaker_profile writeback path", rows[1]["recommended_action"])


if __name__ == "__main__":
    unittest.main()
