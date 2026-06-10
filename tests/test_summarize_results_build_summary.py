from __future__ import annotations

import unittest

from src.summarize_results import build_summary


class SummarizeResultsBuildSummaryTest(unittest.TestCase):
    def test_build_summary_includes_gold_cases(self) -> None:
        rows = build_summary()
        case_ids = {row["case_id"] for row in rows}
        self.assertIn("NoOverlap", case_ids)

    def test_build_summary_selects_lowest_cer_method(self) -> None:
        rows = build_summary()
        no_overlap = next(row for row in rows if row["case_id"] == "NoOverlap")
        self.assertEqual(no_overlap["best_method"], "separated_whisper")
        self.assertLess(float(no_overlap["separated_cer"]), float(no_overlap["mixed_cer"]))

    def test_build_summary_includes_case_observations(self) -> None:
        rows = build_summary()
        no_overlap = next(row for row in rows if row["case_id"] == "NoOverlap")
        self.assertIn("Separated speaker-track ASR", no_overlap["observation"])


if __name__ == "__main__":
    unittest.main()
