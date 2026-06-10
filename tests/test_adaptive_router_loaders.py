from __future__ import annotations

import unittest

from src.adaptive_router import load_benchmark_rows, load_cer_rows, load_cleaned_rows


class AdaptiveRouterLoadersTest(unittest.TestCase):
    def test_load_benchmark_rows_indexes_gold_cases(self) -> None:
        mixed, separated = load_benchmark_rows()
        self.assertIn("NoOverlap", mixed)
        self.assertIn("NoOverlap", separated)

    def test_load_cer_rows_indexes_case_method_pairs(self) -> None:
        cer_lookup = load_cer_rows()
        self.assertIn(("NoOverlap", "mixed_whisper"), cer_lookup)
        self.assertGreater(cer_lookup[("NoOverlap", "mixed_whisper")], 0.0)

    def test_load_cleaned_rows_indexes_cleaned_transcripts(self) -> None:
        cleaned = load_cleaned_rows()
        self.assertIn("NoOverlap", cleaned)
        self.assertIn("cleaned_segments", cleaned["NoOverlap"])


if __name__ == "__main__":
    unittest.main()
