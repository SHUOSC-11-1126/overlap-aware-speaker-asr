from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_runbook_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierExecutionReceiptFillExecutionRunbookBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_links_runbook_to_evidence_receipt(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "recommended_frontier": "meeteval_compatibility",
                "runbook_note": "Start with meeteval_compatibility.",
            }
        )

        self.assertIn("evidence_receipt", rows[0]["receipt_target"])


if __name__ == "__main__":
    unittest.main()
