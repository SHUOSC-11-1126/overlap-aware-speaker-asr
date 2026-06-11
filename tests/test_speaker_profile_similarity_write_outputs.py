from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_similarity import CSV_COLUMNS, write_outputs


def _sample_similarity_row() -> dict[str, object]:
    return {
        "case_id": "FixtureCase",
        "best_profile_alignment": "direct",
        "direct_profile_score": 0.9,
        "swapped_profile_score": 0.1,
        "profile_confidence_gap": 0.8,
        "hypothesis_source": "separated_whisper",
        "observation": "fixture observation",
    }


class SpeakerProfileSimilarityWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_similarity_and_derived_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.speaker_profile_similarity.PROJECT_ROOT", root):
                outputs = write_outputs([_sample_similarity_row()])

            for path in outputs:
                self.assertTrue(path.exists(), msg=str(path))

            csv_path, json_path, md_path = outputs[0], outputs[1], outputs[2]
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, CSV_COLUMNS)
                self.assertEqual(list(reader)[0]["case_id"], "FixtureCase")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["best_profile_alignment"], "direct")
            self.assertIn("Speaker Profile Risk Summary", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
