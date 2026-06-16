from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.separation_phase_boundary import BOUNDARY_COLUMNS, DENSE_TREND_COLUMNS, write_outputs


def _sample_metadata() -> dict[str, object]:
    return {
        "boundary_type": "crosses_to_harmful",
        "crossover_ratio": 0.35,
        "crossover_ci_lower": 0.25,
        "crossover_ci_median": 0.35,
        "crossover_ci_upper": 0.45,
        "crossover_ci_width": 0.20,
        "bootstrap_samples": 100,
        "below_boundary_help_rate": 0.85,
        "above_boundary_help_rate": 0.15,
        "label": "experimental/frontier",
    }


def _sample_dense_trend() -> list[dict[str, object]]:
    return [
        {
            "overlap_bin": 0.0,
            "sample_count": 2,
            "mean_delta_cer_separated": -0.25,
            "median_delta_cer_separated": -0.25,
            "separation_help_rate": 1.0,
            "source_labels": "test",
            "bootstrap_mean_delta_cer": -0.26,
            "bootstrap_se_cer": 0.01,
            "bootstrap_p_helps": 1.0,
            "trend_ci_lower": -0.28,
            "trend_ci_upper": -0.24,
        },
    ]


class SeparationPhaseBoundaryWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.separation_phase_boundary.PROJECT_ROOT", root):
                paths = write_outputs(
                    _sample_metadata(), _sample_dense_trend()
                )

            for path in paths:
                self.assertTrue(path.exists(), msg=str(path))

            boundary_csv, boundary_json, trend_csv, trend_json, boundary_md = paths

            with boundary_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, BOUNDARY_COLUMNS)
                rows = list(reader)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["boundary_type"], "crosses_to_harmful")

            payload = json.loads(boundary_json.read_text(encoding="utf-8"))
            self.assertIsInstance(payload, dict)
            self.assertEqual(payload["boundary_type"], "crosses_to_harmful")
            self.assertAlmostEqual(float(payload["crossover_ratio"]), 0.35, places=4)

            with trend_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                trend_reader = csv.DictReader(handle)
                self.assertEqual(trend_reader.fieldnames, DENSE_TREND_COLUMNS)
                trend_r = list(trend_reader)
                self.assertEqual(len(trend_r), 1)
                self.assertAlmostEqual(
                    float(trend_r[0]["bootstrap_p_helps"]), 1.0, places=2
                )

            trend_payload = json.loads(trend_json.read_text(encoding="utf-8"))
            self.assertIsInstance(trend_payload, list)
            self.assertEqual(len(trend_payload), 1)

            markdown = boundary_md.read_text(encoding="utf-8")
            self.assertIn("experimental/frontier", markdown)
            self.assertIn("crosses_to_harmful", markdown)


if __name__ == "__main__":
    unittest.main()
