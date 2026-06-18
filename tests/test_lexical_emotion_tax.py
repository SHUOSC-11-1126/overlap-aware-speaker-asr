"""Tests for the lexical-emotion separation-tax pure logic (experimental/frontier).

Pin the tri-modal agreement summarizer: per-overlap means, pairwise correlation, and sign-agreement
fractions across the CER / acoustic / lexical benefits. No Whisper/librosa (benefits passed in).
"""
from __future__ import annotations

import unittest

from src.lexical_emotion_tax import agreement_summary


class TestAgreementSummary(unittest.TestCase):
    def _rows(self, triples):
        return [{"overlap_ratio": ov, "cer_benefit": c, "acoustic_benefit": a, "lexical_benefit": l}
                for ov, c, a, l in triples]

    def test_all_agree(self) -> None:
        # CER and lexical move together (same signs) -> high agreement + positive correlation
        rows = self._rows([(0.1, -0.5, 0.2, -0.4), (0.3, -0.3, 0.2, -0.2),
                           (0.6, 0.4, 0.3, 0.5), (0.9, 0.6, 0.3, 0.7)])
        s = agreement_summary(rows)
        self.assertAlmostEqual(s["sign_agree_cer_lexical"], 1.0, places=6)
        self.assertGreater(s["pearson_cer_lexical"], 0.9)

    def test_acoustic_disagrees_with_cer(self) -> None:
        # acoustic always positive, CER negative at low overlap -> they disagree there
        rows = self._rows([(0.1, -0.5, 0.2, -0.4), (0.3, -0.3, 0.2, -0.2),
                           (0.6, 0.4, 0.3, 0.5), (0.9, 0.6, 0.3, 0.7)])
        s = agreement_summary(rows)
        self.assertLess(s["sign_agree_cer_acoustic"], 1.0)

    def test_by_overlap_means(self) -> None:
        rows = self._rows([(0.1, -0.5, 0.2, -0.4), (0.1, -0.3, 0.4, -0.2)])
        s = agreement_summary(rows)
        b = s["by_overlap"][0]
        self.assertAlmostEqual(b["mean_cer_benefit"], -0.4, places=6)
        self.assertAlmostEqual(b["mean_acoustic_benefit"], 0.3, places=6)

    def test_keys_present(self) -> None:
        s = agreement_summary(self._rows([(0.1, -0.5, 0.2, -0.4), (0.6, 0.4, 0.3, 0.5)]))
        for k in ("pearson_cer_lexical", "pearson_cer_acoustic", "pearson_acoustic_lexical",
                  "sign_agree_cer_lexical", "sign_agree_cer_acoustic", "by_overlap", "n"):
            self.assertIn(k, s)


if __name__ == "__main__":
    unittest.main()
