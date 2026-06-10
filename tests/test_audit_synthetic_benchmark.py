from __future__ import annotations

import unittest

from src.audit_synthetic_benchmark import get_hypothesis_text, get_reference_text, safe_preview


class AuditSyntheticBenchmarkPreviewTest(unittest.TestCase):
    def test_safe_preview_collapses_whitespace(self) -> None:
        self.assertEqual(safe_preview("line one\n\nline two"), "line one line two")

    def test_safe_preview_truncates_to_limit(self) -> None:
        self.assertEqual(len(safe_preview("a" * 300, limit=100)), 100)


class AuditSyntheticBenchmarkTextExtractionTest(unittest.TestCase):
    def test_get_reference_text_prefers_full_text(self) -> None:
        self.assertEqual(get_reference_text({"full_text": "ref", "text": "alt"}), "ref")

    def test_get_hypothesis_text_prefers_full_text(self) -> None:
        self.assertEqual(
            get_hypothesis_text({"full_text": "hyp", "cleaned_full_text": "clean", "text": "alt"}),
            "hyp",
        )


if __name__ == "__main__":
    unittest.main()
