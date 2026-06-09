from __future__ import annotations

import unittest

from src.meeteval_cpwer_tokenization_gain_scorecard_handoff_completion_summary_bridge_checklist import (
    build_bridge_checklist_rows,
)


class MeetEvalCpwerTokenizationGainScorecardHandoffCompletionSummaryBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_when_queue_complete(self) -> None:
        summary = {
            "queue_status": "queue_complete",
            "handoff_status": "tokenization_gain_handoff_ready",
            "adapted_and_aligned_count": "5",
            "case_count": "5",
        }

        rows = build_bridge_checklist_rows(summary)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["queue_status"], "queue_complete")

    def test_build_bridge_checklist_rows_empty_when_summary_missing(self) -> None:
        self.assertEqual(build_bridge_checklist_rows({}), [])


if __name__ == "__main__":
    unittest.main()
