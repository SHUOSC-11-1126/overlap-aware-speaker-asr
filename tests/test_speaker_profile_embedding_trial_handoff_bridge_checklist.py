from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_handoff_bridge_checklist import build_bridge_checklist_rows


class SpeakerProfileEmbeddingTrialHandoffBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_method_execution(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "case_id": "NoOverlap",
                "trial_status": "scaffold_only",
                "profile_confidence_gap": "0.15",
            }
        )

        self.assertEqual(rows[0]["case_id"], "NoOverlap")
        self.assertIn("method execution", rows[0]["next_gate"].lower())


if __name__ == "__main__":
    unittest.main()
