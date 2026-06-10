from __future__ import annotations

import unittest

from src.analyze_cer_errors import (
    extract_hypothesis_text,
    find_repeated_phrases,
    hypothesis_path_for,
)


class AnalyzeCerErrorsTest(unittest.TestCase):
    def test_hypothesis_path_for_mixed_whisper(self) -> None:
        path = hypothesis_path_for("LightOverlap", "mixed_whisper")
        self.assertTrue(path.name.endswith("LightOverlap_mixed_whisper.json"))
        self.assertIn("transcripts_raw", path.as_posix())

    def test_hypothesis_path_for_separated_whisper(self) -> None:
        path = hypothesis_path_for("NoOverlap", "separated_whisper")
        self.assertTrue(path.name.endswith("NoOverlap_separated_speaker_transcript.json"))
        self.assertIn("transcripts_speaker", path.as_posix())

    def test_extract_hypothesis_text_uses_text_field_for_mixed(self) -> None:
        payload = {"text": "混合文本", "full_text": "ignored"}
        self.assertEqual(extract_hypothesis_text(payload, "mixed_whisper"), "混合文本")

    def test_extract_hypothesis_text_uses_full_text_for_separated(self) -> None:
        payload = {"text": "ignored", "full_text": "分离文本"}
        self.assertEqual(extract_hypothesis_text(payload, "separated_whisper"), "分离文本")

    def test_find_repeated_phrases_detects_repeated_clause(self) -> None:
        text = "同意这个观点\n同意这个观点\n其他内容"
        phrases = find_repeated_phrases(text)
        clause_hits = [p for p in phrases if p["type"] == "repeated_clause"]
        self.assertTrue(any(p["phrase"] == "同意这个观点" and p["count"] >= 2 for p in clause_hits))

    def test_find_repeated_phrases_detects_high_frequency_chunk(self) -> None:
        text = "abcdefghabcdefghabcdefgh"
        phrases = find_repeated_phrases(text)
        chunk_hits = [p for p in phrases if p["type"] == "high_frequency_chunk"]
        self.assertTrue(any(p["count"] >= 3 for p in chunk_hits))


if __name__ == "__main__":
    unittest.main()
