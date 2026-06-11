from __future__ import annotations

import unittest

from src.meeteval_gold_cer_cpwer_reconciliation import (
    build_reconciliation_rows,
    build_summary_rows,
)


class MeetevalGoldCerCpwerReconciliationTest(unittest.TestCase):
    def test_build_reconciliation_rows_marks_exact_match(self) -> None:
        meeteval_rows = [
            {
                "case_id": "NoOverlap",
                "hypothesis_source": "separated_whisper",
                "official_cpwer": "0.053957",
                "tokenization_mode": "character_spaced",
            }
        ]
        cer_lookup = {("NoOverlap", "separated_whisper"): 0.053957}
        rows = build_reconciliation_rows(meeteval_rows, cer_lookup)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["reconciled"])
        self.assertEqual(rows[0]["gap_direction"], "match")

    def test_build_summary_rows_reports_rate(self) -> None:
        rows = [{"reconciled": True, "absolute_gap": 0.0}, {"reconciled": False, "absolute_gap": 0.1}]
        summary = build_summary_rows(rows)
        metrics = {row["metric"]: row["value"] for row in summary}
        self.assertEqual(metrics["reconciliation_rate"], "0.5")


if __name__ == "__main__":
    unittest.main()
