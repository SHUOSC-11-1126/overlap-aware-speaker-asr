from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.plot_results import write_table_outputs


def _sample_row() -> dict[str, object]:
    return {
        "case_id": "FixtureCase",
        "overlap_level": 0,
        "mixed_cer": 0.2,
        "separated_cer": 0.05,
        "separated_cleaned_cer": 0.09,
        "best_method": "separated_whisper",
        "best_cer": 0.05,
        "observation": "fixture",
    }


class PlotResultsWriteTableOutputsTest(unittest.TestCase):
    def test_write_table_outputs_emits_csv_and_json_payload(self) -> None:
        averages = {
            "mixed_whisper": 0.2,
            "separated_whisper": 0.05,
            "separated_whisper_cleaned": 0.09,
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.plot_results.PROJECT_ROOT", root):
                csv_path, json_path = write_table_outputs([_sample_row()], averages)

            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())

            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["best_method"], "separated_whisper")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["average_cer"]["mixed_average"], 0.2)
            self.assertEqual(payload["rows"][0]["case_id"], "FixtureCase")


if __name__ == "__main__":
    unittest.main()
