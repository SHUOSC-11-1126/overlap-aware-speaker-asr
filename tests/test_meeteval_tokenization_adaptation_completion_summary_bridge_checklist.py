from __future__ import annotations

import unittest

from src.meeteval_cpwer_tokenization_adaptation_completion_summary_bridge_checklist import (
    build_bridge_checklist_rows,
)


class MeetEvalTokenizationAdaptationCompletionSummaryBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_frontier_fill(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "queue_status": "queue_complete",
                "aligned_count": "5",
                "total_count": "5",
            }
        )

        self.assertEqual(rows[0]["queue_status"], "queue_complete")
        self.assertIn("operator_brief", rows[0]["receipt_target"])


if __name__ == "__main__":
    unittest.main()
