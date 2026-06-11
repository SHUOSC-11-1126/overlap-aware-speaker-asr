from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.router_boundary_alignment import ALIGNMENT_COLUMNS, SUMMARY_COLUMNS, write_outputs


def _alignment_row() -> dict[str, object]:
    return {
        "case_id": "FixtureCase",
        "overlap_ratio_anchor": 0.15,
        "selected_method": "mixed_whisper",
        "oracle_method": "mixed_whisper",
        "mixed_cer": 0.21,
        "separated_cer": 0.48,
        "separated_cleaned_cer": 0.38,
        "selected_cer": 0.21,
        "oracle_cer": 0.21,
        "delta_cer_separated": 0.27,
        "separation_helps": False,
        "prefers_separation_route": False,
        "router_matches_oracle": True,
        "router_aligns_with_phase": True,
        "router_regret_cer": 0.0,
        "decision_rule": "fixture rule",
    }


def _summary_row() -> dict[str, str]:
    return {
        "metric": "router_phase_alignment_rate",
        "value": "1.0",
        "label": "experimental/frontier",
    }


class RouterBoundaryAlignmentWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.router_boundary_alignment.PROJECT_ROOT", root):
                paths = write_outputs([_alignment_row()], [_summary_row()])

            for path in paths:
                self.assertTrue(path.exists(), msg=str(path))

            csv_path, json_path, summary_csv_path, summary_json_path, md_path = paths
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, ALIGNMENT_COLUMNS)
                self.assertEqual(list(reader)[0]["case_id"], "FixtureCase")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertTrue(payload[0]["router_aligns_with_phase"])

            with summary_csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                summary_reader = csv.DictReader(handle)
                self.assertEqual(summary_reader.fieldnames, SUMMARY_COLUMNS)

            markdown = md_path.read_text(encoding="utf-8")
            self.assertIn("experimental/frontier", markdown)
            self.assertIn("FixtureCase", markdown)


if __name__ == "__main__":
    unittest.main()
