from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.error_type_boundary_report import BOUNDARY_COLUMNS, SUMMARY_COLUMNS, write_outputs


def _boundary_row() -> dict[str, object]:
    return {
        "case_id": "LightOverlap",
        "overlap_ratio_anchor": 0.15,
        "method": "separated_whisper",
        "cer": 0.475,
        "dominant_error_type": "insertion",
        "insertion_count": 54,
        "repetition_count": 38,
        "removed_count_if_cleaned": 0,
        "delta_cer_separated": 0.264286,
        "separation_helps": False,
        "insertion_heavy": True,
        "explains_separation_harm": True,
    }


class ErrorTypeBoundaryReportWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        summary = [{"metric": "gold_case_count", "value": "1", "label": "stable/gold"}]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.error_type_boundary_report.PROJECT_ROOT", root):
                paths = write_outputs([_boundary_row()], summary)

            for path in paths:
                self.assertTrue(path.exists(), msg=str(path))

            csv_path, json_path, _, _, md_path = paths
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, BOUNDARY_COLUMNS)

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertTrue(payload[0]["explains_separation_harm"])

            markdown = md_path.read_text(encoding="utf-8")
            self.assertIn("experimental/frontier", markdown)
            self.assertIn("LightOverlap", markdown)


if __name__ == "__main__":
    unittest.main()
