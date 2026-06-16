from __future__ import annotations

import unittest

from src.hallucination_cure_eval import CURES, aggregate_by_cure


class TestCuresMatrix(unittest.TestCase):
    def test_every_cure_well_formed(self) -> None:
        for name, spec in CURES.items():
            self.assertIn("kwargs", spec, name)
            self.assertIn("trim", spec, name)
            self.assertIsInstance(spec["trim"], bool, name)

    def test_native_cures_require_word_timestamps(self) -> None:
        for name in ("halluc_silence", "halluc_silence_trim"):
            kw = CURES[name]["kwargs"]
            self.assertTrue(kw.get("word_timestamps"), name)
            self.assertIn("hallucination_silence_threshold", kw, name)

    def test_trim_flags(self) -> None:
        self.assertFalse(CURES["greedy_baseline"]["trim"])
        self.assertTrue(CURES["silence_trim"]["trim"])
        self.assertTrue(CURES["halluc_silence_trim"]["trim"])

    def test_beam_cure(self) -> None:
        self.assertEqual(CURES["beam5"]["kwargs"].get("beam_size"), 5)


class TestAggregateByCure(unittest.TestCase):
    def test_per_cure_stats_and_tail(self) -> None:
        rows = [
            {"cure": "greedy_baseline", "cer": "24.0"},
            {"cure": "greedy_baseline", "cer": "0.4"},
            {"cure": "silence_trim", "cer": "0.5"},
            {"cure": "silence_trim", "cer": "0.6"},
        ]
        agg = {r["cure"]: r for r in aggregate_by_cure(rows)}
        g = agg["greedy_baseline"]
        self.assertEqual(g["n"], 2)
        self.assertAlmostEqual(g["mean_cer"], 12.2)
        self.assertAlmostEqual(g["median_cer"], 12.2)
        self.assertAlmostEqual(g["tail_rate"], 0.5)   # one of two > 1.0
        self.assertAlmostEqual(g["max_cer"], 24.0)
        t = agg["silence_trim"]
        self.assertAlmostEqual(t["tail_rate"], 0.0)   # none catastrophic
        self.assertAlmostEqual(t["mean_cer"], 0.55)

    def test_missing_cure_omitted(self) -> None:
        rows = [{"cure": "beam5", "cer": "0.3"}]
        names = [r["cure"] for r in aggregate_by_cure(rows)]
        self.assertEqual(names, ["beam5"])  # only cures with samples appear


if __name__ == "__main__":
    unittest.main()
