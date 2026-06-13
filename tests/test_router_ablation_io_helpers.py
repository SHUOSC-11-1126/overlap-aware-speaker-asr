from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.config import PROJECT_ROOT, load_config
from src.router_ablation import load_case_map, read_csv_rows, read_json, to_float, to_int


class RouterAblationIoHelpersTest(unittest.TestCase):
    def test_to_int_and_to_float_parse_numeric_strings(self) -> None:
        self.assertEqual(to_int("3"), 3)
        self.assertAlmostEqual(to_float("0.5"), 0.5)
        self.assertEqual(to_int("bad"), 0)
        self.assertIsNone(to_float("bad"))

    def test_read_csv_rows_raises_for_missing_file(self) -> None:
        missing = PROJECT_ROOT / "results" / "tables" / "__missing_router_ablation__.csv"
        with self.assertRaises(FileNotFoundError):
            read_csv_rows(missing)

    def test_read_csv_rows_loads_dict_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "rows.csv"
            with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.DictWriter(handle, fieldnames=["case_id", "method"])
                writer.writeheader()
                writer.writerow({"case_id": "NoOverlap", "method": "mixed_whisper"})
            rows = read_csv_rows(csv_path)
        self.assertEqual(rows[0]["case_id"], "NoOverlap")

    def test_read_json_loads_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = Path(tmp_dir) / "payload.json"
            json_path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            payload = read_json(json_path)
        self.assertEqual(payload["value"], 1)

    def test_load_case_map_indexes_by_case_id(self) -> None:
        case_map = load_case_map(load_config())
        self.assertIn("NoOverlap", case_map)
        self.assertEqual(case_map["NoOverlap"]["id"], "NoOverlap")


if __name__ == "__main__":
    unittest.main()
