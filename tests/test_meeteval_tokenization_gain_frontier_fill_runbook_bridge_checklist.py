from __future__ import annotations

import unittest

from src.meeteval_tokenization_gain_frontier_fill_runbook_bridge_checklist import (
    build_bridge_checklist_rows,
)


class MeetEvalTokenizationGainFrontierFillRunbookBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_links_runbook_card_to_execution_receipt(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "runbook_status": "tokenization_gain_frontier_fill_runbook_ready",
                "recommended_frontier": "meeteval_compatibility",
                "adapted_case_ratio": "5/5",
                "next_action": "Execute the real frontier run.",
                "completion_signal": "execution_status is no longer template_only",
                "guardrail_note": "Full MeetEval benchmark completion is not claimed.",
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertIn("meeteval_tokenization_gain_frontier_fill_runbook_card", rows[0]["prerequisite_artifact"])
        self.assertEqual(rows[0]["execution_receipt_target"], "results/tables/meeteval_cpwer_execution_receipt.json")
        self.assertIn("5/5", rows[0]["bridge_note"])
        self.assertIn("not claimed", rows[0]["guardrail_note"])

    def test_build_bridge_checklist_rows_empty_when_runbook_missing(self) -> None:
        self.assertEqual(build_bridge_checklist_rows({}), [])


if __name__ == "__main__":
    unittest.main()
