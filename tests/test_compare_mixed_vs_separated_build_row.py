from __future__ import annotations

import unittest

from src.compare_mixed_vs_separated import build_row
from src.config import get_audio_cases, load_config


class CompareMixedVsSeparatedBuildRowTest(unittest.TestCase):
    def test_build_row_joins_mixed_and_separated_transcripts(self) -> None:
        config = load_config()
        case = next(case for case in get_audio_cases(config) if case["id"] == "NoOverlap")
        row = build_row(case)
        self.assertEqual(row["case_id"], "NoOverlap")
        self.assertGreater(row["mixed_text_length"], 0)
        self.assertGreater(row["separated_text_length"], 0)
        self.assertIn("mixed_transcript_path", row)
        self.assertIn("separated_transcript_path", row)


if __name__ == "__main__":
    unittest.main()
