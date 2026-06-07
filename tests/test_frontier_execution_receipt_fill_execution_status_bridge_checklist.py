from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_status_bridge_checklist import build_bridge_checklist_rows


class FrontierExecutionReceiptFillExecutionStatusBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_uses_fill_execution_ready(self) -> None:
        rows = build_bridge_checklist_rows({"combined_fill_execution_status": "fill_execution_ready"})

        self.assertEqual(rows[0]["combined_fill_execution_status"], "fill_execution_ready")


if __name__ == "__main__":
    unittest.main()
