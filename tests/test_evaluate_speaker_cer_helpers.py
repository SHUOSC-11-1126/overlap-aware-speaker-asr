from __future__ import annotations

import unittest

from src.evaluate_speaker_cer import aggregate_speaker_text, compute_cer


class EvaluateSpeakerCerHelpersTest(unittest.TestCase):
    def test_aggregate_speaker_text_joins_matching_segments(self) -> None:
        text = aggregate_speaker_text(
            [
                {"speaker": "SPEAKER_1", "text": "甲"},
                {"speaker": "SPEAKER_2", "text": "乙"},
                {"speaker": "SPEAKER_1", "text": "丙"},
            ],
            "SPEAKER_1",
        )
        self.assertEqual(text, "甲丙")

    def test_compute_cer_returns_macro_metrics(self) -> None:
        result = compute_cer("你好世界", "你好世")
        self.assertEqual(result["cer"], 0.25)
        self.assertEqual(result["edit_distance"], 1)


if __name__ == "__main__":
    unittest.main()
