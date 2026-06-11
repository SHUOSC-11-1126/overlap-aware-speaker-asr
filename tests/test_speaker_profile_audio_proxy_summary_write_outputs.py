from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_audio_proxy_summary import (
    SUMMARY_COLUMNS,
    build_audio_proxy_summary_row,
    write_outputs,
)


class SpeakerProfileAudioProxySummaryWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_summary_artifacts(self) -> None:
        row = build_audio_proxy_summary_row(
            [
                {
                    "best_audio_alignment": "direct",
                    "audio_confidence_gap": "0.15",
                },
                {
                    "best_audio_alignment": "swapped",
                    "audio_confidence_gap": "0.05",
                },
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.speaker_profile_audio_proxy_summary.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SUMMARY_COLUMNS)
                self.assertEqual(list(reader)[0]["case_count"], "2")
            self.assertIn("Audio Proxy Summary", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
