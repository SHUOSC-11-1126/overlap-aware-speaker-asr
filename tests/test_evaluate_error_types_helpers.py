from __future__ import annotations

import unittest

from src.evaluate_error_types import (
    detect_repetition,
    dominant_error_type,
    levenshtein_alignment_counts,
    segment_texts,
    transcript_text,
)


class EvaluateErrorTypesHelpersTest(unittest.TestCase):
    def test_dominant_error_type_prefers_highest_count(self) -> None:
        self.assertEqual(dominant_error_type(1, 5, 2, repetition_count=0), "deletion")
        self.assertEqual(dominant_error_type(1, 1, 4, repetition_count=2), "insertion")

    def test_detect_repetition_counts_adjacent_duplicates(self) -> None:
        payload = {
            "segments": [
                {"text": "重复句子"},
                {"text": "重复句子"},
                {"text": "其他内容"},
            ]
        }
        count = detect_repetition(payload, "separated_whisper")
        self.assertGreaterEqual(count, 1)

    def test_segment_texts_filters_empty_segments(self) -> None:
        payload = {"segments": [{"text": "你好"}, {"text": "  "}, {"text": "世界"}]}
        self.assertEqual(segment_texts(payload, "mixed_whisper"), ["你好", "世界"])

    def test_transcript_text_selects_field_by_method(self) -> None:
        payload = {"text": "混合", "full_text": "分离", "cleaned_full_text": "清理"}
        self.assertEqual(transcript_text(payload, "mixed_whisper"), "混合")
        self.assertEqual(transcript_text(payload, "separated_whisper"), "分离")
        self.assertEqual(transcript_text(payload, "separated_whisper_cleaned"), "清理")

    def test_levenshtein_alignment_counts_reports_edit_breakdown(self) -> None:
        subs, dels, ins, total = levenshtein_alignment_counts("你好世界", "你好世")
        self.assertEqual(total, 1)
        self.assertEqual(subs + dels + ins, 1)


if __name__ == "__main__":
    unittest.main()
