from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from src.summarize_results import read_csv_rows, to_float


class SummarizeResultsHelpersTest(unittest.TestCase):
    def test_to_float_returns_none_for_blank_values(self) -> None:
        self.assertIsNone(to_float(None))
        self.assertIsNone(to_float(""))
        self.assertIsNone(to_float("not-a-number"))

    def test_to_float_parses_numeric_strings(self) -> None:
        self.assertEqual(to_float("0.215827"), 0.215827)

    def test_read_csv_rows_returns_empty_for_missing_file(self) -> None:
        missing = Path("/tmp/__missing_summarize_rows__.csv")
        self.assertEqual(read_csv_rows(missing), [])

    def test_read_csv_rows_loads_dict_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "rows.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["case_id", "cer"])
                writer.writeheader()
                writer.writerow({"case_id": "NoOverlap", "cer": "0.1"})
            rows = read_csv_rows(csv_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["case_id"], "NoOverlap")


if __name__ == "__main__":
    unittest.main()
