from __future__ import annotations

import unittest
from unittest.mock import patch

from src.meeteval_cpwer_official_execution import (
    build_execution_row,
    build_speaker_text_lists,
    merge_receipt_entry,
)


class MeetEvalCpwerOfficialExecutionTest(unittest.TestCase):
    def test_build_execution_row_when_tool_unavailable(self) -> None:
        row = build_execution_row("NoOverlap", "separated_whisper", None, 2, tool_available=False)

        self.assertEqual(row["execution_status"], "official_cpwer_tool_unavailable")
        self.assertEqual(row["cpwer_tool"], "unavailable")

    def test_build_execution_row_when_complete(self) -> None:
        row = build_execution_row("NoOverlap", "separated_whisper", 0.12, 2, tool_available=True)

        self.assertEqual(row["execution_status"], "official_cpwer_narrow_dry_run_complete")
        self.assertEqual(row["official_cpwer"], "0.12")

    def test_build_speaker_text_lists_aligns_by_speaker(self) -> None:
        reference = [
            {"speaker": "SPEAKER_1", "text": "你好"},
            {"speaker": "SPEAKER_2", "text": "世界"},
        ]
        hypothesis = [
            {"speaker": "SPEAKER_1", "text": "你好啊"},
            {"speaker": "SPEAKER_2", "text": "世界"},
        ]
        ref_texts, hyp_texts = build_speaker_text_lists(reference, hypothesis, ["SPEAKER_1", "SPEAKER_2"])

        self.assertEqual(ref_texts, ["你好", "世界"])
        self.assertEqual(hyp_texts, ["你好啊", "世界"])

    def test_merge_receipt_entry_updates_official_fields(self) -> None:
        with patch(
            "src.meeteval_cpwer_official_execution.load_bridge_lite_score",
            return_value="0.15",
        ):
            merged = merge_receipt_entry(
                {"case_id": "NoOverlap", "execution_status": "template_only"},
                {
                    "case_id": "NoOverlap",
                    "execution_status": "official_cpwer_narrow_dry_run_complete",
                    "official_cpwer": "0.12",
                    "cpwer_tool": "meeteval",
                    "result_label": "experimental/frontier",
                    "execution_note": "done",
                },
            )

        self.assertEqual(merged["official_cpwer"], "0.12")
        self.assertEqual(merged["cpwer_bridge_lite"], "0.15")


if __name__ == "__main__":
    unittest.main()
