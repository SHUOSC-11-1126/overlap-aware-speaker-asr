from __future__ import annotations

import unittest

from src.risk_aware_selector import (
    aggregate_speaker_text,
    classify_risk,
    repeat_phrase_count,
)


class RiskAwareSelectorHelpersTest(unittest.TestCase):
    def test_aggregate_speaker_text_joins_matching_segments(self) -> None:
        text = aggregate_speaker_text(
            [
                {"speaker": "SPEAKER_1", "text": "你好"},
                {"speaker": "SPEAKER_2", "text": "世界"},
                {"speaker": "SPEAKER_1", "text": "再见"},
            ],
            "SPEAKER_1",
        )
        self.assertEqual(text, "你好再见")

    def test_repeat_phrase_count_detects_repeated_chunks(self) -> None:
        self.assertGreater(repeat_phrase_count("同意这个观点同意这个观点"), 0)
        self.assertEqual(repeat_phrase_count(""), 0)

    def test_classify_risk_returns_low_for_benign_features(self) -> None:
        risk_level, reasons = classify_risk(
            {
                "repetition_count": 0,
                "text_length_ratio": 1.1,
                "speaker_length_imbalance": 0.1,
                "duplicate_removed_count": 0,
                "cleaned_text": "",
                "cleaned_to_separated_ratio": 1.0,
                "method_disagreement_score": 0.1,
            }
        )
        self.assertEqual(risk_level, "low")
        self.assertEqual(reasons, ["low_risk"])


if __name__ == "__main__":
    unittest.main()
