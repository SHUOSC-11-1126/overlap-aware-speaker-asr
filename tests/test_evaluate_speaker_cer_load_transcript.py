from __future__ import annotations

import unittest

from src.evaluate_speaker_cer import load_speaker_transcript


class EvaluateSpeakerCerLoadTranscriptTest(unittest.TestCase):
    def test_load_speaker_transcript_reads_separated_file(self) -> None:
        path, payload = load_speaker_transcript("NoOverlap", "separated_whisper")
        self.assertTrue(path.exists())
        self.assertEqual(payload.get("case_id"), "NoOverlap")

    def test_load_speaker_transcript_reads_cleaned_file(self) -> None:
        path, payload = load_speaker_transcript("NoOverlap", "separated_whisper_cleaned")
        self.assertTrue(path.exists())
        self.assertIn("cleaned_full_text", payload)

    def test_load_speaker_transcript_raises_for_missing_case(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_speaker_transcript("__missing_case__", "separated_whisper")

    def test_load_speaker_transcript_rejects_unsupported_method(self) -> None:
        with self.assertRaises(ValueError):
            load_speaker_transcript("NoOverlap", "mixed_whisper")


if __name__ == "__main__":
    unittest.main()
