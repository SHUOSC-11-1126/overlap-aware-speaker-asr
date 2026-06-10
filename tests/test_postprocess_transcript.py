from __future__ import annotations

import unittest

from src.postprocess_transcript import (
    build_full_text,
    get_case_ids,
    load_cases,
    normalized_text,
    process_segments,
    should_remove_segment,
    similarity,
)


class PostprocessTranscriptTest(unittest.TestCase):
    def test_normalized_text_strips_punctuation_and_whitespace(self) -> None:
        self.assertEqual(normalized_text("你好，世界！"), "你好世界")
        self.assertEqual(normalized_text("a b\nc"), "abc")

    def test_should_remove_segment_flags_empty_text(self) -> None:
        remove, reason = should_remove_segment({"text": "  ", "speaker": "S1"}, [], {})
        self.assertTrue(remove)
        self.assertEqual(reason, "empty_text")

    def test_should_remove_segment_flags_adjacent_exact_duplicate(self) -> None:
        kept = [{"text": "重复内容", "speaker": "S1"}]
        remove, reason = should_remove_segment({"text": "重复内容", "speaker": "S1"}, kept, {})
        self.assertTrue(remove)
        self.assertEqual(reason, "exact_duplicate_adjacent")

    def test_process_segments_keeps_unique_segments(self) -> None:
        segments = [
            {"speaker": "S1", "text": "第一句"},
            {"speaker": "S1", "text": "第二句"},
        ]
        cleaned, removed = process_segments(segments)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(len(removed), 0)

    def test_process_segments_removes_duplicates(self) -> None:
        segments = [
            {"speaker": "S1", "text": "重复"},
            {"speaker": "S1", "text": "重复"},
        ]
        cleaned, removed = process_segments(segments)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0]["reason"], "exact_duplicate_adjacent")

    def test_build_full_text_formats_speaker_labels(self) -> None:
        text = build_full_text([{"speaker": "S1", "text": "你好"}])
        self.assertEqual(text, "[S1] 你好")

    def test_similarity_returns_high_score_for_near_duplicates(self) -> None:
        self.assertGreaterEqual(similarity("你好世界", "你好世"), 0.8)
        self.assertLess(similarity("你好", "再见"), 0.5)

    def test_get_case_ids_returns_single_case_or_all(self) -> None:
        self.assertEqual(get_case_ids("NoOverlap"), ["NoOverlap"])
        self.assertIn("NoOverlap", get_case_ids("all"))

    def test_load_cases_returns_configured_audio_cases(self) -> None:
        cases = load_cases()
        self.assertGreater(len(cases), 0)
        self.assertTrue(all("id" in case for case in cases))


if __name__ == "__main__":
    unittest.main()
