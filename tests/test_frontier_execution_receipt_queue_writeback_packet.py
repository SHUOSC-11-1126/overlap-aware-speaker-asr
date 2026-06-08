from __future__ import annotations

import unittest

from src.frontier_execution_receipt_queue_writeback_packet import build_packet_rows


class FrontierExecutionReceiptQueueWritebackPacketTest(unittest.TestCase):
    def test_build_packet_rows_includes_seven_sections(self) -> None:
        rows = build_packet_rows(
            {"queue_status": "queue_complete", "ready_receipt_count": "3", "pending_receipt_count": "0"}
        )

        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[0]["section_name"], "receipt_queue_operator_brief")


if __name__ == "__main__":
    unittest.main()
