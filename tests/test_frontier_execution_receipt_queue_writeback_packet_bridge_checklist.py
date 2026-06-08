from __future__ import annotations

import unittest

from src.frontier_execution_receipt_queue_writeback_packet_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierExecutionReceiptQueueWritebackPacketBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_operator_brief(self) -> None:
        rows = build_bridge_checklist_rows(
            {"queue_status": "queue_complete", "ready_receipt_count": "3", "pending_receipt_count": "0"}
        )

        self.assertEqual(rows[0]["queue_status"], "queue_complete")
        self.assertIn("operator_brief", rows[0]["receipt_target"])


if __name__ == "__main__":
    unittest.main()
