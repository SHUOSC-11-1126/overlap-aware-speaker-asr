from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.build_synthetic_references import read_csv_rows, read_json


class BuildSyntheticReferencesIoHelpersTest(unittest.TestCase):
    def test_read_csv_rows_loads_manifest_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "manifest.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["sample_id", "tier"])
                writer.writeheader()
                writer.writerow({"sample_id": "s1", "tier": "SyntheticNoOverlap"})
            rows = read_csv_rows(csv_path)
        self.assertEqual(rows[0]["sample_id"], "s1")

    def test_read_csv_rows_raises_for_missing_file(self) -> None:
        from src.config import PROJECT_ROOT

        missing = PROJECT_ROOT / "results" / "tables" / "__missing_synthetic_manifest__.csv"
        with self.assertRaises(FileNotFoundError):
            read_csv_rows(missing)

    def test_read_json_loads_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = Path(tmp_dir) / "payload.json"
            json_path.write_text(json.dumps({"text": "demo"}), encoding="utf-8")
            payload = read_json(json_path)
        self.assertEqual(payload["text"], "demo")


if __name__ == "__main__":
    unittest.main()
