from __future__ import annotations

import unittest

from src.compare_mixed_vs_separated import preview, upsert_row


class CompareMixedVsSeparatedHelpersTest(unittest.TestCase):
    def test_preview_collapses_whitespace_and_truncates(self) -> None:
        text = "你好   世界\n测试"
        self.assertEqual(preview(text, limit=10), "你好 世界 测试"[:10])

    def test_upsert_row_replaces_matching_case_and_model(self) -> None:
        rows = [{"case_id": "A", "model": "whisper-base", "mixed_text_length": 10}]
        updated = upsert_row(rows, {"case_id": "A", "model": "whisper-base", "mixed_text_length": 20})
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["mixed_text_length"], 20)

    def test_upsert_row_appends_new_case(self) -> None:
        rows = [{"case_id": "A", "model": "whisper-base"}]
        updated = upsert_row(rows, {"case_id": "B", "model": "whisper-base"})
        self.assertEqual(len(updated), 2)


if __name__ == "__main__":
    unittest.main()
