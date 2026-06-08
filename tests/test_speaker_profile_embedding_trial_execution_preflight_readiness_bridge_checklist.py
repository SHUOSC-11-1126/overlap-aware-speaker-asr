from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_preflight_readiness_bridge_checklist import (
    build_bridge_checklist_rows,
)


class SpeakerProfilePreflightReadinessBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_execution_receipt(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "readiness_status": "preflight_ready",
                "case_id": "NoOverlap",
                "preflight_pass": "True",
            }
        )

        self.assertEqual(rows[0]["readiness_status"], "preflight_ready")
        self.assertIn("execution_receipt", rows[0]["receipt_target"])


if __name__ == "__main__":
    unittest.main()
