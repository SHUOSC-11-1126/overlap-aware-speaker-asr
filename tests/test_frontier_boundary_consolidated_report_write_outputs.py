from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_boundary_consolidated_report import FINDING_COLUMNS, SECTION_COLUMNS, write_outputs


class FrontierBoundaryConsolidatedReportWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_section_and_finding_artifacts(self) -> None:
        section_rows = [{"section": "router_boundary", "metric": "gold_case_count", "value": "5", "label": "experimental/frontier"}]
        finding_rows = [
            {
                "finding_id": "F1",
                "source_module": "separation_phase_diagram",
                "statement": "fixture",
                "label": "experimental/frontier",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.frontier_boundary_consolidated_report.PROJECT_ROOT", root):
                paths = write_outputs(section_rows, finding_rows)

            for path in paths:
                self.assertTrue(path.exists(), msg=str(path))

            with paths[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SECTION_COLUMNS)

            with paths[2].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, FINDING_COLUMNS)

            self.assertIn("experimental/frontier", paths[4].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
