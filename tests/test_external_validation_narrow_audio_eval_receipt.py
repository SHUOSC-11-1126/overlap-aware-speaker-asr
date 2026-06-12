from __future__ import annotations

import unittest

from src.external_validation_narrow_audio_eval_receipt import build_receipt_row, build_writeup_row


class ExternalValidationNarrowAudioEvalReceiptTest(unittest.TestCase):
    def test_build_receipt_row_marks_narrow_asr_complete(self) -> None:
        row = build_receipt_row(
            {
                "dataset_name": "AISHELL-4",
                "slice_id": "stub",
                "result_label": "external/sanity-check",
                "model": "whisper-tiny",
                "eval_status": "narrow_asr_complete",
                "text_length": "51",
                "transcript_path": "results/external_sanity_check/transcripts/stub_whisper.json",
            }
        )
        self.assertEqual(row["execution_status"], "narrow_asr_complete")
        self.assertEqual(row["blocker"], "none_documented")

    def test_fill_eval_receipt_requires_completed_eval(self) -> None:
        from unittest.mock import patch

        from src.external_validation_narrow_audio_eval_receipt import fill_eval_receipt

        with patch(
            "src.external_validation_narrow_audio_eval_receipt.load_json_dict",
            return_value={"eval_status": "pending"},
        ):
            with self.assertRaises(RuntimeError):
                fill_eval_receipt()


if __name__ == "__main__":
    unittest.main()
