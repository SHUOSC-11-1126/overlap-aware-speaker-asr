from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.adaptive_router_v2 import read_csv_rows, read_json


class AdaptiveRouterV2IoHelpersTest(unittest.TestCase):
    def test_read_csv_rows_loads_dict_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "rows.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["case_id", "selected_method"])
                writer.writeheader()
                writer.writerow({"case_id": "NoOverlap", "selected_method": "mixed_whisper"})
            rows = read_csv_rows(csv_path)
        self.assertEqual(rows[0]["case_id"], "NoOverlap")

    def test_read_json_loads_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = Path(tmp_dir) / "payload.json"
            json_path.write_text(json.dumps({"segments": []}), encoding="utf-8")
            payload = read_json(json_path)
        self.assertEqual(payload, {"segments": []})


if __name__ == "__main__":
    unittest.main()
