from __future__ import annotations

import unittest

from src.evaluate_cpcer_lite import aggregate_speaker_text, compute_cer, macro_cer_for_mapping, sanitize_rows


class EvaluateCpcerLiteHelpersTest(unittest.TestCase):
    def test_macro_cer_for_mapping_direct_and_swapped(self) -> None:
        direct_macro, _, _ = macro_cer_for_mapping(
            "你好世界",
            "再见朋友",
            "你好世",
            "再见朋",
            "direct",
        )
        swapped_macro, _, _ = macro_cer_for_mapping(
            "你好世界",
            "再见朋友",
            "再见朋",
            "你好世",
            "swapped",
        )
        self.assertEqual(direct_macro, swapped_macro)
        self.assertGreater(direct_macro, 0.0)

    def test_sanitize_rows_deduplicates_and_skips_incomplete_rows(self) -> None:
        rows = sanitize_rows(
            [
                {"case_id": "Demo", "method": "separated_whisper"},
                {"case_id": "Demo", "method": "separated_whisper"},
                {"case_id": "", "method": "mixed_whisper"},
            ]
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["case_id"], "Demo")

    def test_aggregate_speaker_text_joins_matching_segments(self) -> None:
        text = aggregate_speaker_text(
            [
                {"speaker": "SPEAKER_1", "text": "甲"},
                {"speaker": "SPEAKER_2", "text": "乙"},
                {"speaker": "SPEAKER_1", "text": "丙"},
            ],
            "SPEAKER_1",
        )
        self.assertEqual(text, "甲丙")

    def test_compute_cer_returns_normalized_edit_metrics(self) -> None:
        result = compute_cer("你好世界", "你好世")
        self.assertEqual(result["cer"], 0.25)
        self.assertEqual(result["edit_distance"], 1)


if __name__ == "__main__":
    unittest.main()
