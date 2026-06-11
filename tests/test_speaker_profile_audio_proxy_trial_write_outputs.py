from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_audio_proxy_trial import AUDIO_PROXY_COLUMNS, write_outputs


def _sample_audio_proxy_row() -> dict[str, str]:
    return {
        "case_id": "FixtureCase",
        "hypothesis_source": "separated_whisper",
        "best_audio_alignment": "direct",
        "direct_audio_score": "0.91",
        "swapped_audio_score": "0.12",
        "audio_confidence_gap": "0.79",
        "result_label": "experimental/frontier",
        "observation": "fixture audio proxy note",
    }


class SpeakerProfileAudioProxyTrialWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_audio_proxy_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.speaker_profile_audio_proxy_trial.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs([_sample_audio_proxy_row()])

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists(), msg=str(path))

            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, AUDIO_PROXY_COLUMNS)
                self.assertEqual(list(reader)[0]["case_id"], "FixtureCase")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["best_audio_alignment"], "direct")
            self.assertIn("Audio Proxy Trial", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
