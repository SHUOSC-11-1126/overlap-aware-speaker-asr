from __future__ import annotations

import unittest

from src.meeteval_tokenization_gain_to_frontier_fill_handoff_bridge_checklist import (
    build_bridge_checklist_rows,
)


class MeetEvalTokenizationGainToFrontierFillHandoffBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_when_handoff_ready(self) -> None:
        handoff = {
            "handoff_status": "tokenization_gain_frontier_fill_handoff_ready",
            "queue_status": "queue_complete",
            "adapted_and_aligned_count": "5",
            "case_count": "5",
        }

        rows = build_bridge_checklist_rows(handoff)

        self.assertEqual(len(rows), 1)
        self.assertIn("operator_brief", rows[0]["receipt_target"])

    def test_build_bridge_checklist_rows_empty_when_handoff_missing(self) -> None:
        self.assertEqual(build_bridge_checklist_rows({}), [])


if __name__ == "__main__":
    unittest.main()
