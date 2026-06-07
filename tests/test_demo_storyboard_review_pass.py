from __future__ import annotations

import unittest

from src.demo_storyboard_review_pass import build_review_receipt_rows, build_review_row


class DemoStoryboardReviewPassTest(unittest.TestCase):
    def test_build_review_row_records_first_card(self) -> None:
        row = build_review_row({"title": "Problem", "body": "test"}, card_index=1)

        self.assertEqual(row["card_title"], "Problem")
        self.assertEqual(row["review_status"], "review_complete")

    def test_build_review_receipt_rows_document_review(self) -> None:
        rows = build_review_receipt_rows({"card_index": "1"}, 4)

        self.assertEqual(rows[0]["execution_status"], "review_complete")
        self.assertEqual(rows[0]["card_count"], "4")


if __name__ == "__main__":
    unittest.main()
