from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_handoff_packet import (
    build_handoff_packet_rows,
)


class FrontierExecutionReceiptFillExecutionHandoffPacketTest(unittest.TestCase):
    def test_build_handoff_packet_rows_include_operator_and_receipt_bridge(self) -> None:
        rows = build_handoff_packet_rows()
        sections = {row["packet_section"] for row in rows}

        self.assertIn("operator", sections)
        self.assertIn("receipt_bridge", sections)
        self.assertIn("entry", sections)


if __name__ == "__main__":
    unittest.main()
