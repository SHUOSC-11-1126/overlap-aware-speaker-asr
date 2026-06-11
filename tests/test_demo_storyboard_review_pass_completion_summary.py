from __future__ import annotations

import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from src.demo_storyboard_review_pass_completion_summary import (
    build_completion_summary_lines,
    build_completion_summary_row,
    write_outputs,
)


class DemoStoryboardReviewPassCompletionSummaryTest(unittest.TestCase):
    def test_build_completion_summary_row_marks_queue_complete_when_no_pending(self) -> None:
        row = build_completion_summary_row(
            {
                "completed_count": "4",
                "total_card_count": "4",
                "pending_count": "0",
            }
        )
        self.assertEqual(row["queue_status"], "queue_complete")
        self.assertIn("qualitative/demo", row["observation"].lower())

    def test_build_completion_summary_row_marks_in_progress_when_pending(self) -> None:
        row = build_completion_summary_row(
            {
                "completed_count": "2",
                "total_card_count": "4",
                "pending_count": "2",
            }
        )
        self.assertEqual(row["queue_status"], "queue_in_progress")

    def test_build_completion_summary_lines_render_table_header(self) -> None:
        row = build_completion_summary_row(
            {
                "completed_count": "1",
                "total_card_count": "2",
                "pending_count": "1",
            }
        )
        rendered = "\n".join(build_completion_summary_lines(row))
        self.assertIn("# Demo Storyboard Review Pass Completion Summary", rendered)
        self.assertIn("| scope | completed_count |", rendered)
        self.assertIn("storyboard_review_queue", rendered)

    def test_write_outputs_creates_status_and_completion_artifacts(self) -> None:
        status_row = {
            "queue_status": "queue_in_progress",
            "completed_count": "2",
            "total_card_count": "4",
            "pending_count": "2",
            "status_note": "Storyboard review queue at 2/4; no live demo or recording delivery is claimed.",
        }
        completion_row = build_completion_summary_row(status_row)
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with unittest.mock.patch("src.demo_storyboard_review_pass_completion_summary.PROJECT_ROOT", root):
                paths = write_outputs(status_row, completion_row)
                for path in paths:
                    self.assertTrue(path.exists())
                completion_json = json.loads(paths[4].read_text(encoding="utf-8"))
                completion_md = paths[5].read_text(encoding="utf-8")
        self.assertEqual(completion_json["queue_status"], "queue_in_progress")
        self.assertIn("qualitative/demo", completion_md.lower())


if __name__ == "__main__":
    unittest.main()
