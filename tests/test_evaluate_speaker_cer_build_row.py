from __future__ import annotations

import unittest

from src.evaluate_speaker_cer import build_row


class EvaluateSpeakerCerBuildRowTest(unittest.TestCase):
    def test_build_row_computes_speaker_macro_cer_for_gold_case(self) -> None:
        row = build_row("NoOverlap", "separated_whisper")
        self.assertEqual(row["case_id"], "NoOverlap")
        self.assertEqual(row["method"], "separated_whisper")
        self.assertIn("speaker_macro_cer", row)
        self.assertGreaterEqual(row["speaker_macro_cer"], 0.0)
        self.assertIn("Speaker-aware CER", row["observation"])


if __name__ == "__main__":
    unittest.main()
