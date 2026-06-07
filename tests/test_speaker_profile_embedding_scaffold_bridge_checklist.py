from __future__ import annotations

import unittest

from src.speaker_profile_embedding_scaffold_bridge_checklist import (
    build_bridge_checklist_lines,
    build_bridge_checklist_rows,
)


class SpeakerProfileEmbeddingScaffoldBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_use_scaffold(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "scaffold_status": "scaffold_only",
                "method_direction": "embedding_or_voiceprint_baseline",
            }
        )

        self.assertEqual(rows[0]["scaffold_status"], "scaffold_only")
        self.assertIn("scaffold_only", rows[0]["bridge_note"])

    def test_build_bridge_checklist_lines_render_note(self) -> None:
        lines = build_bridge_checklist_lines(
            [
                {
                    "checklist_order": "1",
                    "scaffold_status": "scaffold_only",
                    "prerequisite_artifact": "results/figures/speaker_profile_embedding_scaffold.md",
                    "receipt_target": "results/figures/speaker_profile_method_receipt.md",
                    "checklist_goal": "Verify the embedding scaffold bridge.",
                    "bridge_note": "Scaffold remains scaffold_only.",
                    "next_gate": "Confirm this bridge before opening the speaker profile method receipt target.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Speaker Profile Embedding Scaffold Bridge Checklist", rendered)


if __name__ == "__main__":
    unittest.main()
