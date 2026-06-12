from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.config import PROJECT_ROOT
from src.external_validation_narrow_audio_eval import (
    build_eval_row,
    build_summary_rows,
    transcript_path,
)


class ExternalValidationNarrowAudioEvalTest(unittest.TestCase):
    def test_build_eval_row_marks_external_sanity_check(self) -> None:
        row = build_eval_row(
            {"audio_path": "resources/external_sanity_check/aishell4/meeting_excerpt_stub_001.wav"},
            {"dataset_name": "AISHELL-4", "slice_id": "aishell4_meeting_excerpt_stub_001", "label": "external/sanity-check"},
            {"model": "whisper-tiny", "text": "你好", "segments": [{"start": 0.0, "end": 1.0, "text": "你好"}], "runtime_sec": 1.2},
            PROJECT_ROOT / "results/external_sanity_check/transcripts/aishell4_meeting_excerpt_stub_001_whisper.json",
        )
        self.assertEqual(row["eval_status"], "narrow_asr_complete")
        self.assertEqual(row["result_label"], "external/sanity-check")
        self.assertIn("no gold CER", row["observation"])

    def test_build_summary_rows_include_eval_status(self) -> None:
        rows = build_summary_rows({"eval_status": "narrow_asr_complete", "model": "whisper-tiny", "text_length": "12"})
        self.assertEqual(rows[0]["metric"], "eval_status")

    def test_run_narrow_eval_requires_prerequisites(self) -> None:
        from src.external_validation_narrow_audio_eval import run_narrow_eval

        with patch("src.external_validation_narrow_audio_eval.mini_check_audio_ready", return_value=False):
            with self.assertRaises(RuntimeError):
                run_narrow_eval()

    def test_transcript_path_uses_slice_id(self) -> None:
        path = transcript_path("aishell4_meeting_excerpt_stub_001")
        self.assertTrue(str(path).endswith("aishell4_meeting_excerpt_stub_001_whisper.json"))


if __name__ == "__main__":
    unittest.main()
