from __future__ import annotations

import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from src.project_harness import build_report, write_frontier_status_checklist, write_report


class ProjectHarnessWriteOutputsTest(unittest.TestCase):
    def test_write_report_writes_json_and_markdown_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with unittest.mock.patch("src.project_harness.PROJECT_ROOT", root):
                report = build_report()
                json_path, md_path = write_report(report)
                loaded = json.loads(json_path.read_text(encoding="utf-8"))
                markdown = md_path.read_text(encoding="utf-8")
        self.assertIn("gold_cases", loaded)
        self.assertIn("frontier_status", loaded)
        self.assertIn("core_files_present", loaded)
        self.assertIn("# Project Harness Report", markdown)
        self.assertIn("## Frontier Status", markdown)
        self.assertIn("speaker_profile", markdown)

    def test_write_frontier_status_checklist_writes_csv_json_and_markdown(self) -> None:
        frontier_status = [
            {
                "frontier_id": "speaker_profile",
                "status": "documented_skill",
                "evidence_path": "docs/skills/skill_01_speaker_profile.md",
                "expected_output": "triage",
                "next_step": "stronger profile method",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with unittest.mock.patch("src.project_harness.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_frontier_status_checklist(frontier_status)
                self.assertTrue(csv_path.exists())
                self.assertTrue(json_path.exists())
                self.assertTrue(md_path.exists())
                markdown = md_path.read_text(encoding="utf-8")
                rows = json.loads(json_path.read_text(encoding="utf-8"))
                self.assertGreaterEqual(len(rows), 1)
                self.assertIn("speaker_profile", markdown)


if __name__ == "__main__":
    unittest.main()
