from __future__ import annotations

import unittest

from src.llm_critic_qualitative_brief_light_mid import (
    build_brief_row,
    build_summary_rows,
)


class LlmCriticQualitativeBriefLightMidTest(unittest.TestCase):
    def test_build_brief_row_flags_insertion_harm(self) -> None:
        cer_lookup = {
            ("LightOverlap", "mixed_whisper"): 0.21,
            ("LightOverlap", "separated_whisper"): 0.475,
            ("LightOverlap", "separated_whisper_cleaned"): 0.38,
        }
        error_lookup = {
            ("LightOverlap", "mixed_whisper"): {"dominant_error_type": "insertion"},
            ("LightOverlap", "separated_whisper"): {
                "dominant_error_type": "insertion",
                "insertion_count": "54",
                "repetition_count": "38",
            },
        }
        row = build_brief_row("LightOverlap", cer_lookup, error_lookup, {})
        self.assertEqual(row["separation_harm_observed"], "True")
        self.assertIn("insertion-heavy", row["critic_hypothesis"])
        self.assertEqual(row["result_label"], "qualitative/demo")

    def test_build_summary_rows_counts_harm(self) -> None:
        rows = [
            {"separation_harm_observed": "True", "dominant_error_separated": "insertion"},
            {"separation_harm_observed": "True", "dominant_error_separated": "deletion"},
        ]
        summary = {row["metric"]: row["value"] for row in build_summary_rows(rows)}
        self.assertEqual(summary["separation_harm_rate"], "1.0")
        self.assertEqual(summary["insertion_driven_harm_count"], "1")


if __name__ == "__main__":
    unittest.main()
