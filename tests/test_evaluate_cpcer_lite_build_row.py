from __future__ import annotations

import unittest

from src.evaluate_cpcer_lite import build_row


class EvaluateCpcerLiteBuildRowTest(unittest.TestCase):
    def test_build_row_reports_direct_and_swapped_macro_cer(self) -> None:
        row = build_row("NoOverlap", "separated_whisper")
        self.assertEqual(row["case_id"], "NoOverlap")
        self.assertIn("direct_speaker_macro_cer", row)
        self.assertIn("swapped_speaker_macro_cer", row)
        self.assertIn("cpcer_lite", row)
        self.assertIn(row["best_mapping"], {"direct", "swapped"})


if __name__ == "__main__":
    unittest.main()
