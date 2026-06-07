from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_scaffold_bridge_checklist import build_bridge_checklist_rows


class SpeakerProfileEmbeddingTrialExecutionScaffoldBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_voiceprint_execution(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "case_id": "NoOverlap",
                "scaffold_status": "execution_scaffold_only",
                "profile_confidence_gap": "0.15",
            }
        )

        self.assertEqual(rows[0]["case_id"], "NoOverlap")
        self.assertIn("voiceprint", rows[0]["next_gate"].lower())


if __name__ == "__main__":
    unittest.main()
