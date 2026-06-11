from __future__ import annotations

import csv
import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from src.evaluate_cpcer_lite import render_markdown, write_outputs


class EvaluateCpcerLiteWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_writes_csv_and_json_tables(self) -> None:
        rows = [
            {
                "case_id": "NoOverlap",
                "method": "separated_whisper",
                "cpcer_lite": 0.05,
                "direct_speaker_macro_cer": 0.06,
                "swapped_speaker_macro_cer": 0.08,
                "speaker_assignment_gap": 0.01,
            }
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with unittest.mock.patch("src.evaluate_cpcer_lite.PROJECT_ROOT", root):
                csv_path, json_path = write_outputs(rows)
            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                loaded_csv = list(csv.DictReader(handle))
            loaded_json = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(loaded_csv[0]["case_id"], "NoOverlap")
        self.assertEqual(loaded_json[0]["cpcer_lite"], 0.05)

    def test_render_markdown_writes_summary_with_case_table(self) -> None:
        rows = [
            {
                "case_id": "NoOverlap",
                "method": method,
                "cpcer_lite": 0.05,
                "direct_speaker_macro_cer": 0.06,
                "swapped_speaker_macro_cer": 0.08,
                "speaker_assignment_gap": 0.01,
                "best_mapping": "direct",
            }
            for method in ("separated_whisper", "separated_whisper_cleaned")
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            figure_path = root / "results" / "figures" / "cpcer_lite_by_case.png"
            csv_path = root / "results" / "tables" / "cpcer_lite_results.csv"
            figure_path.parent.mkdir(parents=True)
            csv_path.parent.mkdir(parents=True)
            with unittest.mock.patch("src.evaluate_cpcer_lite.PROJECT_ROOT", root):
                md_path = render_markdown(rows, figure_path, csv_path)
            content = md_path.read_text(encoding="utf-8")
        self.assertIn("# cpCER-lite Summary", content)
        self.assertIn("NoOverlap", content)


if __name__ == "__main__":
    unittest.main()
