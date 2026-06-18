"""Tests for the offline regex/lexicon lexical-emotion extractor (experimental/frontier).

Pin the deterministic keyword/regex sentiment logic: polarity counting, negation flipping within a
character window, intensifier scaling, arousal cues, and the text-distance used by the lexical
separation-tax. No model, no network — pure regex over Chinese text.
"""
from __future__ import annotations

import unittest

from src.lexical_emotion import emotion_vector, lexical_distance, lexical_emotion


class TestPolarity(unittest.TestCase):
    def test_positive_text(self) -> None:
        v = lexical_emotion("我支持这个观点，非常好，很有希望")
        self.assertGreater(v["valence"], 0)
        self.assertGreater(v["n_pos"], 0)

    def test_negative_text(self) -> None:
        v = lexical_emotion("这是错误的，我反对，很危险")
        self.assertLess(v["valence"], 0)
        self.assertGreater(v["n_neg"], 0)

    def test_neutral_text(self) -> None:
        v = lexical_emotion("今天的天气是晴天")
        self.assertEqual(v["valence"], 0.0)


class TestNegation(unittest.TestCase):
    def test_negation_flips_positive(self) -> None:
        plain = lexical_emotion("我支持")
        negated = lexical_emotion("我不支持")
        self.assertGreater(plain["valence"], 0)
        self.assertLess(negated["valence"], 0)  # 不+支持 -> negative

    def test_negation_flips_negative(self) -> None:
        negated = lexical_emotion("没有危险")
        self.assertGreaterEqual(negated["valence"], 0)  # 没有+危险 -> not negative

    def test_negation_window_limited(self) -> None:
        # negator far away (beyond the window) should NOT flip the later positive word
        far = lexical_emotion("不是这样的，但是我真的很支持这个非常好的提议")
        self.assertGreater(far["valence"], 0)


class TestIntensifierAndArousal(unittest.TestCase):
    def test_intensifier_raises_magnitude(self) -> None:
        plain = lexical_emotion("好")
        strong = lexical_emotion("非常好")
        self.assertGreater(abs(strong["valence"]), abs(plain["valence"]))

    def test_arousal_from_exclamation_and_intensity(self) -> None:
        calm = lexical_emotion("这个观点可以接受")
        excited = lexical_emotion("这绝对是极其重要的！必须支持！")
        self.assertGreater(excited["arousal"], calm["arousal"])

    def test_empty_text_is_safe(self) -> None:
        v = lexical_emotion("")
        self.assertEqual(v["valence"], 0.0)
        self.assertEqual(v["arousal"], 0.0)


class TestEmotionVectorAndDistance(unittest.TestCase):
    def test_emotion_vector_tuple(self) -> None:
        val, ar = emotion_vector("非常好，很支持！")
        self.assertGreater(val, 0)
        self.assertGreater(ar, 0)

    def test_distance_zero_to_self(self) -> None:
        t = "我强烈反对这个危险的提议"
        d = lexical_distance(t, t)
        self.assertAlmostEqual(d["valence_dist"], 0.0, places=6)
        self.assertAlmostEqual(d["arousal_dist"], 0.0, places=6)
        self.assertAlmostEqual(d["combined"], 0.0, places=6)

    def test_distance_detects_polarity_flip(self) -> None:
        # an ASR error flipping 支持->反对 should register large lexical-emotion distortion
        d = lexical_distance("我支持这个提议", "我反对这个提议")
        self.assertGreater(d["valence_dist"], 0)
        self.assertGreater(d["combined"], 0)

    def test_distance_small_for_emotion_preserving_error(self) -> None:
        # an ASR error that does not touch emotion words -> small lexical-emotion distortion
        d_emotion = lexical_distance("我支持这个提议", "我反对这个提议")
        d_neutral = lexical_distance("我支持这个提议", "我支持这个题议")  # 提->题 typo, emotion intact
        self.assertLess(d_neutral["combined"], d_emotion["combined"])


if __name__ == "__main__":
    unittest.main()
