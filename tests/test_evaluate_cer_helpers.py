from __future__ import annotations

import unittest

from src.evaluate_cer import compute_cer, list_verified_cases, normalize_text


class EvaluateCerHelpersTest(unittest.TestCase):
    def test_normalize_text_strips_speaker_tags_and_punctuation(self) -> None:
        self.assertEqual(normalize_text("[SPEAKER_1] 你好，世界"), "你好世界")

    def test_compute_cer_returns_edit_distance_ratio(self) -> None:
        result = compute_cer("你好世界", "你好世")
        self.assertEqual(result["edit_distance"], 1)
        self.assertEqual(result["reference_length"], 4)
        self.assertEqual(result["cer"], 0.25)

    def test_list_verified_cases_returns_five_gold_cases(self) -> None:
        cases = list_verified_cases()
        self.assertEqual(len(cases), 5)
        self.assertIn("NoOverlap", cases)


if __name__ == "__main__":
    unittest.main()
