from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.project_harness import build_report, write_report


class WriteOutputsTest(unittest.TestCase):
    def test_write_report_writes_json_and_markdown(self) -> None:
        report = build_report()
        with tempfile.TemporaryDirectory() as d:
            json_path, md_path = write_report(report, out_dir=Path(d))
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("gold_cases", payload)
            self.assertIn("core_files_present", payload)


if __name__ == "__main__":
    unittest.main()
