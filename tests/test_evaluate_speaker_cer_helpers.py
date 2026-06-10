from __future__ import annotations

import unittest

from src.evaluate_speaker_cer import aggregate_speaker_text, compute_cer, sanitize_rows, upsert_row


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

    def test_sanitize_rows_deduplicates_case_method_pairs(self) -> None:
        rows = sanitize_rows(
            [
                {"case_id": "Demo", "method": "mixed_whisper"},
                {"case_id": "Demo", "method": "mixed_whisper"},
                {"case_id": "", "method": "mixed_whisper"},
            ]
        )
        self.assertEqual(len(rows), 1)

    def test_upsert_row_replaces_existing_case_method_row(self) -> None:
        rows = [{"case_id": "A", "method": "mixed_whisper", "cer": 0.1}]
        updated = upsert_row(rows, {"case_id": "A", "method": "mixed_whisper", "cer": 0.2})
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["cer"], 0.2)


if __name__ == "__main__":
    unittest.main()
