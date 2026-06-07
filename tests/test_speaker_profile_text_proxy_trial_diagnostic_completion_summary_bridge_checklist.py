from __future__ import annotations

import unittest

from src.speaker_profile_text_proxy_trial_diagnostic_completion_summary_bridge_checklist import (
    build_bridge_checklist_rows,
)


class SpeakerProfileTextProxyTrialDiagnosticCompletionSummaryBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_embedding_handoff(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "queue_status": "queue_complete",
                "swapped_count": "5",
                "case_count": "5",
            }
        )

        self.assertEqual(rows[0]["queue_status"], "queue_complete")
        self.assertIn("embedding_trial_handoff", rows[0]["receipt_target"])


if __name__ == "__main__":
    unittest.main()
