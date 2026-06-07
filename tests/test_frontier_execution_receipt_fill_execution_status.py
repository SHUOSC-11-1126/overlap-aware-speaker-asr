from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_status import (
    build_status_row,
    derive_fill_execution_status,
)


class FrontierExecutionReceiptFillExecutionStatusTest(unittest.TestCase):
    def test_derive_fill_execution_status_awaiting_for_template(self) -> None:
        self.assertEqual(derive_fill_execution_status("template_only"), "awaiting_fill")

    def test_build_status_row_reports_fill_execution_ready(self) -> None:
        row = build_status_row()

        self.assertEqual(row["combined_fill_execution_status"], "fill_execution_ready")
        self.assertEqual(row["meeteval_fill_execution_status"], "awaiting_fill")


if __name__ == "__main__":
    unittest.main()
