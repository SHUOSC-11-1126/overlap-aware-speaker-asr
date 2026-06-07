from __future__ import annotations

import unittest

from src.frontier_execution_receipt_queue_status_bridge_checklist import build_bridge_checklist_rows


class FrontierExecutionReceiptQueueStatusBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_uses_combined_status(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "combined_readiness_status": "receipt_ready_to_fill",
                "meeteval_readiness_status": "receipt_ready_to_fill",
                "speaker_profile_readiness_status": "receipt_ready_to_fill",
                "external_staging_readiness_status": "receipt_ready_to_fill",
            }
        )

        self.assertEqual(rows[0]["combined_readiness_status"], "receipt_ready_to_fill")


if __name__ == "__main__":
    unittest.main()
