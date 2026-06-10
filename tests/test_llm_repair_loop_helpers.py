from __future__ import annotations

import unittest

from src.llm_repair_loop import _generate_synthetic_asr, get_asr_output_text, get_risk_info


class LlmRepairLoopHelpersTest(unittest.TestCase):
    def test_get_asr_output_text_loads_existing_mixed_transcript(self) -> None:
        text = get_asr_output_text("NoOverlap", "mixed_whisper")
        self.assertTrue(text.strip())

    def test_get_asr_output_text_returns_empty_for_unknown_method(self) -> None:
        self.assertEqual(get_asr_output_text("NoOverlap", "unknown_method"), "")

    def test_get_risk_info_returns_string_for_gold_case(self) -> None:
        info = get_risk_info("NoOverlap")
        self.assertIsInstance(info, str)

    def test_generate_synthetic_asr_is_deterministic_with_seed(self) -> None:
        import random

        random.seed(42)
        first = _generate_synthetic_asr("今天我们开会讨论语音识别系统的问题", error_rate=0.2)
        random.seed(42)
        second = _generate_synthetic_asr("今天我们开会讨论语音识别系统的问题", error_rate=0.2)
        self.assertEqual(first, second)
        self.assertNotEqual(first, "今天我们开会讨论语音识别系统的问题")


if __name__ == "__main__":
    unittest.main()
