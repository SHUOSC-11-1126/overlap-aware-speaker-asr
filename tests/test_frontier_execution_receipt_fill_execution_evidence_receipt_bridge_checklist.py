from __future__ import annotations

import unittest

from src.frontier_execution_receipt_fill_execution_evidence_receipt_bridge_checklist import (
    build_bridge_checklist_rows,
)


class FrontierExecutionReceiptFillExecutionEvidenceReceiptBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_links_handoff_packet_to_evidence_receipt(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "receipt_frontier": "meeteval_compatibility",
                "receipt_note": "Write back after the real run.",
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertIn("handoff_packet", rows[0]["prerequisite_artifact"])


if __name__ == "__main__":
    unittest.main()
