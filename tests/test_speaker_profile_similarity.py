from __future__ import annotations

import unittest

from src.speaker_profile_similarity import (
    build_profile_text,
    build_similarity_rows,
    build_speaker_profile_summary_lines,
    text_overlap_ratio,
)


class SpeakerProfileSimilarityTest(unittest.TestCase):
    def test_text_overlap_ratio_counts_shared_characters(self) -> None:
        self.assertEqual(text_overlap_ratio("甲乙丙", "甲乙"), 0.666667)
        self.assertEqual(text_overlap_ratio("完全不同", "甲乙"), 0.0)

    def test_build_profile_text_merges_snippet_texts(self) -> None:
        text = build_profile_text(
            [
                {"text": "我们支持这个观点"},
                {"text": "这个观点很重要"},
            ]
        )
        self.assertEqual(text, "我们支持这个观点这个观点很重要")

    def test_build_similarity_rows_compare_direct_and_swapped_alignment(self) -> None:
        rows = build_similarity_rows(
            case_ids=["DemoCase"],
            profile_texts={
                "con": "支持这个观点",
                "pro": "反对这个观点",
            },
            references={
                "DemoCase": {
                    "speaker_1_text": "支持这个观点",
                    "speaker_2_text": "反对这个观点",
                }
            },
            hypothesis_texts={
                "DemoCase": {
                    "speaker_1_text": "支持这个观点",
                    "speaker_2_text": "反对这个观点",
                    "hypothesis_source": "separated_whisper",
                }
            },
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["case_id"], "DemoCase")
        self.assertEqual(rows[0]["best_profile_alignment"], "direct")
        self.assertEqual(rows[0]["hypothesis_source"], "separated_whisper")
        self.assertGreater(rows[0]["direct_profile_score"], rows[0]["swapped_profile_score"])
        self.assertIn("lightweight risk signal", rows[0]["observation"])

    def test_build_speaker_profile_summary_lines_render_report(self) -> None:
        lines = build_speaker_profile_summary_lines(
            [
                {
                    "case_id": "DemoCase",
                    "best_profile_alignment": "direct",
                    "direct_profile_score": 1.0,
                    "swapped_profile_score": 0.333333,
                    "profile_confidence_gap": 0.666667,
                    "hypothesis_source": "separated_whisper",
                    "observation": "This is a lightweight risk signal, not speaker identification.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Speaker Profile Risk Summary", rendered)
        self.assertIn("DemoCase", rendered)
        self.assertIn("separated_whisper", rendered)
        self.assertIn("lightweight risk signal", rendered)


if __name__ == "__main__":
    unittest.main()
