from __future__ import annotations

import csv
import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from src.compute_aware_cascade import (
    PARETO_COLUMNS,
    read_csv_rows,
    render_tradeoff_figure,
    write_csv_json,
    write_fallback_png,
    write_pareto_outputs,
    write_runtime_audit_outputs,
)


class ComputeAwareCascadeWriteOutputsTest(unittest.TestCase):
    def test_read_csv_rows_raises_for_missing_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing = Path(tmp_dir) / "missing.csv"
            with unittest.mock.patch("src.compute_aware_cascade.PROJECT_ROOT", Path(tmp_dir)):
                with self.assertRaises(FileNotFoundError):
                    read_csv_rows(missing)

    def test_write_csv_json_writes_matching_csv_and_json_payloads(self) -> None:
        rows = [
            {
                "dataset": "synthetic_split",
                "scope": "ALL",
                "strategy": "fixed_mixed_whisper",
                "average_cer": 0.2,
                "average_compute_cost": 1.5,
                "average_rtf": 0.3,
                "pareto_status": "non_dominated",
                "dominated_by": "",
                "notes": "experimental/frontier",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "pareto.csv"
            json_path = Path(tmp_dir) / "pareto.json"
            write_csv_json(rows, csv_path, json_path, PARETO_COLUMNS)
            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                loaded_csv = list(csv.DictReader(handle))
            loaded_json = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(loaded_csv[0]["strategy"], "fixed_mixed_whisper")
        self.assertEqual(loaded_csv[0]["average_cer"], "0.2")
        self.assertEqual(loaded_json, rows)

    def test_write_pareto_outputs_writes_csv_json_and_summary_markdown(self) -> None:
        rows = [
            {
                "dataset": "synthetic_split",
                "scope": "ALL",
                "strategy": "fixed_mixed_whisper",
                "average_cer": 0.2,
                "average_compute_cost": 1.5,
                "average_rtf": 0.3,
                "pareto_status": "non_dominated",
                "dominated_by": "",
                "notes": "experimental/frontier",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            csv_path = root / "pareto.csv"
            json_path = root / "pareto.json"
            summary_path = root / "pareto.md"
            write_pareto_outputs(rows, csv_path, json_path, summary_path)
            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())
            summary = summary_path.read_text(encoding="utf-8")
            self.assertIn("# Cascade Pareto Frontier Audit", summary)
            self.assertIn("fixed_mixed_whisper", summary)

    def test_write_fallback_png_writes_valid_png_bytes(self) -> None:
        rows = [
            {
                "strategy": "fixed_mixed_whisper",
                "average_cer": 0.2,
                "average_compute_cost": 1.5,
            }
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            png_path = Path(tmp_dir) / "tradeoff.png"
            write_fallback_png(png_path, rows)
            payload = png_path.read_bytes()
        self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(payload), 100)

    def test_write_runtime_audit_outputs_writes_csv_json_and_summary_markdown(self) -> None:
        rows = [
            {
                "dataset": "synthetic_split",
                "scope": "ALL",
                "strategy": "fixed_mixed_whisper",
                "observed_runtime_count": 3,
                "proxy_runtime_count": 1,
                "manual_review_count": 0,
                "case_count": 4,
                "observed_runtime_ratio": 0.75,
                "notes": "experimental/frontier runtime audit",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            csv_path = root / "runtime_audit.csv"
            json_path = root / "runtime_audit.json"
            summary_path = root / "runtime_audit.md"
            write_runtime_audit_outputs(rows, csv_path, json_path, summary_path)
            summary = summary_path.read_text(encoding="utf-8")
            loaded_json = json.loads(json_path.read_text(encoding="utf-8"))
            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                loaded_csv = list(csv.DictReader(handle))
            self.assertEqual(loaded_csv[0]["strategy"], "fixed_mixed_whisper")
            self.assertEqual(loaded_json, rows)
            self.assertIn("# Cascade Runtime Provenance Audit", summary)

    def test_render_tradeoff_figure_uses_fallback_when_matplotlib_unavailable(self) -> None:
        rows = [
            {
                "strategy": "fixed_mixed_whisper",
                "average_cer": 0.2,
                "average_compute_cost": 1.5,
            }
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            png_path = Path(tmp_dir) / "tradeoff.png"
            with unittest.mock.patch.dict("sys.modules", {"matplotlib": None, "matplotlib.pyplot": None}):
                render_tradeoff_figure(rows, png_path)
            payload = png_path.read_bytes()
            self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
