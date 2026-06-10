from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.evaluate_cpcer_lite import read_existing_rows, upsert_row


class EvaluateCpcerLiteReadExistingTest(unittest.TestCase):
    def test_read_existing_rows_returns_empty_for_missing_path(self) -> None:
        self.assertEqual(read_existing_rows(Path("/tmp/__missing_cpcer_table__.csv")), [])

    def test_read_existing_rows_reads_json_rows_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = Path(tmp_dir) / "rows.json"
            json_path.write_text(
                json.dumps({"rows": [{"case_id": "NoOverlap", "method": "separated_whisper", "cpcer_lite": 0.1}]}),
                encoding="utf-8",
            )
            rows = read_existing_rows(json_path)
        self.assertEqual(rows[0]["case_id"], "NoOverlap")

    def test_upsert_row_replaces_existing_case_method_row(self) -> None:
        rows = [{"case_id": "A", "method": "mixed_whisper", "cpcer_lite": 0.1}]
        updated = upsert_row(rows, {"case_id": "A", "method": "mixed_whisper", "cpcer_lite": 0.2})
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["cpcer_lite"], 0.2)


if __name__ == "__main__":
    unittest.main()
