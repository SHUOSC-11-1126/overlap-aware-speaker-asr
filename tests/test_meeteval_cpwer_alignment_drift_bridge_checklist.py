from __future__ import annotations

import unittest

from src.meeteval_cpwer_alignment_drift_bridge_checklist import (
    build_bridge_checklist_lines,
    build_bridge_checklist_rows,
)


class MeetEvalCpwerAlignmentDriftBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_use_receipt(self) -> None:
        rows = build_bridge_checklist_rows([{"drift_case_count": "1"}])

        self.assertEqual(rows[0]["drift_case_count"], "1")
        self.assertIn("drift_case_count=1", rows[0]["bridge_note"])

    def test_build_bridge_checklist_lines_render_note(self) -> None:
        lines = build_bridge_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "drift_case_count": "1",
                    "prerequisite_artifact": "results/figures/meeteval_cpwer_alignment_drift_diagnostic.md",
                    "receipt_target": "results/figures/meeteval_cpwer_alignment_bridge_checklist.md",
                    "checklist_goal": "Verify the alignment drift diagnostic bridge.",
                    "bridge_note": "Drift diagnostic reports drift_case_count=1.",
                    "next_gate": "Confirm this bridge before opening the cpWER alignment bridge checklist target.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval cpWER Alignment Drift Bridge Checklist", rendered)


if __name__ == "__main__":
    unittest.main()
