from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.adaptive_router import read_csv_rows, read_json


class AdaptiveRouterIoHelpersTest(unittest.TestCase):
    def test_read_csv_rows_loads_dict_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "rows.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["case_id", "method"])
                writer.writeheader()
                writer.writerow({"case_id": "NoOverlap", "method": "mixed_whisper"})
            rows = read_csv_rows(csv_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["case_id"], "NoOverlap")

    def test_read_json_loads_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = Path(tmp_dir) / "payload.json"
            json_path.write_text(json.dumps({"segments": []}), encoding="utf-8")
            payload = read_json(json_path)
        self.assertEqual(payload, {"segments": []})

    def test_read_csv_rows_raises_for_missing_file(self) -> None:
        from src.config import PROJECT_ROOT

        missing = PROJECT_ROOT / "results" / "__missing_adaptive_router_table__.csv"
        with self.assertRaises(FileNotFoundError):
            read_csv_rows(missing)


if __name__ == "__main__":
    unittest.main()
