from __future__ import annotations

import unittest

from src.speaker_profile_embedding_scaffold import (
    build_embedding_scaffold_lines,
    build_embedding_scaffold_receipt_lines,
    build_embedding_scaffold_receipt_rows,
    build_embedding_scaffold_row,
)


class SpeakerProfileEmbeddingScaffoldTest(unittest.TestCase):
    def test_build_embedding_scaffold_row_is_scaffold_only(self) -> None:
        row = build_embedding_scaffold_row({"dominant_pattern": "swapped_bias"})

        self.assertEqual(row["method_direction"], "embedding_or_voiceprint_baseline")
        self.assertEqual(row["scaffold_status"], "scaffold_only")
        self.assertIn("diagnostic only", row["scaffold_note"].lower())

    def test_build_embedding_scaffold_lines_render_note(self) -> None:
        lines = build_embedding_scaffold_lines(
            {
                "dominant_pattern": "swapped_bias",
                "method_direction": "embedding_or_voiceprint_baseline",
                "scaffold_status": "scaffold_only",
                "expected_inputs": "con/pro snippet audio plus separated speaker-track transcripts for one verified case.",
                "expected_outputs": "Diagnostic embedding-similarity note comparing direct vs swapped speaker assignment.",
                "scaffold_note": "Template-only stronger-method scaffold.",
            }
        )
        rendered = "\n".join(lines)

        self.assertIn("# Speaker Profile Embedding Scaffold", rendered)
        self.assertIn("swapped_bias", rendered)

    def test_build_embedding_scaffold_receipt_rows_mark_scaffold_complete(self) -> None:
        rows = build_embedding_scaffold_receipt_rows(
            {"method_direction": "embedding_or_voiceprint_baseline", "expected_inputs": "snippets"}
        )

        self.assertEqual(rows[0]["execution_status"], "scaffold_complete")
        self.assertIn("has been executed yet", rows[0]["writeback_note"].lower())

    def test_build_embedding_scaffold_receipt_lines_render_receipt(self) -> None:
        lines = build_embedding_scaffold_receipt_lines(
            [
                {
                    "execution_status": "scaffold_complete",
                    "method_scope": "single_verified_case",
                    "method_direction": "embedding_or_voiceprint_baseline",
                    "expected_inputs": "con/pro snippet audio plus separated speaker-track transcripts for one verified case.",
                    "writeback_note": "Embedding scaffold documented; no stronger speaker-profile method has been executed yet.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("scaffold_complete", rendered)


if __name__ == "__main__":
    unittest.main()
