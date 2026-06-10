from __future__ import annotations

import unittest

from src.rag_repair import format_rag_context, retrieve_relevant_segments, simple_text_similarity


class RagRepairTest(unittest.TestCase):
    def test_simple_text_similarity_is_one_for_identical_text(self) -> None:
        score = simple_text_similarity("你好世界", "你好世界")
        self.assertEqual(score, 1.0)

    def test_simple_text_similarity_is_zero_for_empty_input(self) -> None:
        self.assertEqual(simple_text_similarity("", "你好"), 0.0)

    def test_retrieve_relevant_segments_returns_top_match(self) -> None:
        kb = {
            "case_a": [{"speaker": "S1", "text": "项目进度正常", "start": 0.0, "end": 1.0}],
            "case_b": [{"speaker": "S2", "text": "完全不同的内容", "start": 0.0, "end": 1.0}],
        }
        hits = retrieve_relevant_segments("项目进度正常", kb, top_k=1)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["case_id"], "case_a")
        self.assertGreater(hits[0]["similarity"], 0.5)

    def test_format_rag_context_includes_speaker_and_similarity(self) -> None:
        context = format_rag_context(
            [
                {
                    "similarity": 0.91,
                    "segment": {"speaker": "S1", "text": "测试文本"},
                }
            ]
        )
        self.assertIn("[S1]", context)
        self.assertIn("测试文本", context)
        self.assertIn("0.91", context)


if __name__ == "__main__":
    unittest.main()
