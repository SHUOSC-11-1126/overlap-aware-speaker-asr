from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.audit_synthetic_benchmark import read_csv_rows, read_json, safe_preview
from src.config import PROJECT_ROOT


class AuditSyntheticBenchmarkIoHelpersTest(unittest.TestCase):
    def test_safe_preview_collapses_whitespace(self) -> None:
        self.assertEqual(safe_preview("a\n\tb  c", limit=10), "a b c"[:10])

    def test_read_csv_rows_raises_for_missing_file(self) -> None:
        missing = PROJECT_ROOT / "results" / "tables" / "__missing_audit_rows__.csv"
        with self.assertRaises(FileNotFoundError):
            read_csv_rows(missing)

    def test_read_csv_rows_reads_dict_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "rows.csv"
            with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.DictWriter(handle, fieldnames=["sample_id"])
                writer.writeheader()
                writer.writerow({"sample_id": "sample_001"})
            rows = read_csv_rows(csv_path)
        self.assertEqual(rows[0]["sample_id"], "sample_001")

    def test_read_json_loads_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = Path(tmp_dir) / "payload.json"
            json_path.write_text(json.dumps({"text": "demo"}), encoding="utf-8")
            payload = read_json(json_path)
        self.assertEqual(payload["text"], "demo")


if __name__ == "__main__":
    unittest.main()
