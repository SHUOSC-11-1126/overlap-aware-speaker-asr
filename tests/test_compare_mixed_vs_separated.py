from __future__ import annotations

import unittest

from src.compare_mixed_vs_separated import preview


class CompareMixedVsSeparatedPreviewTest(unittest.TestCase):
    def test_preview_collapses_whitespace(self) -> None:
        self.assertEqual(preview("hello\n\nworld"), "hello world")

    def test_preview_truncates_to_limit(self) -> None:
        text = "a" * 200
        self.assertEqual(len(preview(text, limit=50)), 50)


if __name__ == "__main__":
    unittest.main()
