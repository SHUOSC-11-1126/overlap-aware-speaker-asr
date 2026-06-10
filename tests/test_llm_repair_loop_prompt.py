from __future__ import annotations

import unittest

from src.llm_repair_loop import build_repair_prompt


class LlmRepairLoopPromptTest(unittest.TestCase):
    def test_build_repair_prompt_includes_asr_text_and_case_id(self) -> None:
        messages = build_repair_prompt(
            asr_text="[SPEAKER_1] 方式要调整",
            rag_context="",
            case_id="DemoCase",
        )
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        user = messages[1]["content"]
        self.assertIn("DemoCase", user)
        self.assertIn("方式要调整", user)

    def test_build_repair_prompt_includes_rag_and_risk_sections_when_provided(self) -> None:
        messages = build_repair_prompt(
            asr_text="原文",
            rag_context="参考片段",
            case_id="Case2",
            risk_info="高重叠风险",
        )
        user = messages[1]["content"]
        self.assertIn("参考上下文", user)
        self.assertIn("参考片段", user)
        self.assertIn("高重叠风险", user)


if __name__ == "__main__":
    unittest.main()
