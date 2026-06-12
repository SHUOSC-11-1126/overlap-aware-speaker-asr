from __future__ import annotations

import unittest
from unittest.mock import patch

from src.external_validation_aishell4_excerpt_fetch import (
    build_reference_payload,
    convert_excerpt,
)
from src.external_validation_license_confirmation import CONFIRMED_LICENSE_STATUS


class ExternalValidationAishell4ExcerptFetchTest(unittest.TestCase):
    def test_build_reference_payload_marks_pending_alignment(self) -> None:
        payload = build_reference_payload({"slice_id": "stub", "dataset_name": "AISHELL-4"}, seconds=10)
        self.assertEqual(payload["staging_status"], "audio_excerpt_staged")
        self.assertEqual(payload["segments"][0]["transcript_status"], "pending_external_alignment")

    def test_fetch_excerpt_requires_confirmed_license(self) -> None:
        from src.external_validation_aishell4_excerpt_fetch import fetch_excerpt

        with self.assertRaises(RuntimeError):
            fetch_excerpt({"license_status": "pending_confirmation", "audio_path": "a.wav", "reference_path": "a.json"})

    def test_convert_excerpt_calls_ffmpeg(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            flac = root / "in.flac"
            wav = root / "out.wav"
            flac.write_bytes(b"x")
            with patch("src.external_validation_aishell4_excerpt_fetch.shutil.which", return_value="/usr/bin/ffmpeg"):
                with patch("src.external_validation_aishell4_excerpt_fetch.subprocess.run") as run:
                    convert_excerpt(flac, wav, seconds=5)
            run.assert_called_once()
            self.assertEqual(run.call_args.args[0][0], "ffmpeg")


if __name__ == "__main__":
    unittest.main()
