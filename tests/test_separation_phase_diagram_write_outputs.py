from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.separation_phase_diagram import POINT_COLUMNS, TREND_COLUMNS, write_outputs


def _sample_point() -> dict[str, object]:
    return {
        "point_id": "FixtureCase",
        "source_label": "stable/gold",
        "overlap_ratio": 0.15,
        "overlap_ratio_kind": "tier_anchor",
        "tier": "SyntheticLightOverlap",
        "mixed_cer": 0.21,
        "separated_cer": 0.48,
        "separated_cleaned_cer": 0.38,
        "delta_cer_separated": 0.27,
        "delta_cer_cleaned": 0.17,
        "separation_helps": False,
    }


def _sample_trend() -> dict[str, object]:
    return {
        "overlap_bin": 0.15,
        "sample_count": 1,
        "mean_delta_cer_separated": 0.27,
        "median_delta_cer_separated": 0.27,
        "separation_help_rate": 0.0,
        "source_labels": "stable/gold",
    }


class SeparationPhaseDiagramWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_markdown_and_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.separation_phase_diagram.PROJECT_ROOT", root):
                paths = write_outputs([_sample_point()], [_sample_trend()])

            for path in paths:
                self.assertTrue(path.exists(), msg=str(path))

            csv_path, json_path, trend_csv_path, trend_json_path, md_path, png_path = paths
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, POINT_COLUMNS)
                self.assertEqual(list(reader)[0]["point_id"], "FixtureCase")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["source_label"], "stable/gold")

            with trend_csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                trend_reader = csv.DictReader(handle)
                self.assertEqual(trend_reader.fieldnames, TREND_COLUMNS)

            markdown = md_path.read_text(encoding="utf-8")
            self.assertIn("experimental/frontier", markdown)
            self.assertIn("FixtureCase", markdown)
            self.assertGreater(png_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
