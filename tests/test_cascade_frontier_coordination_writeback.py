from __future__ import annotations

import unittest
from unittest.mock import patch

from src.cascade_frontier_coordination_writeback import (
    build_coordination_rows,
    build_fill_row,
    run_coordination_writeback,
)


class CascadeFrontierCoordinationWritebackTest(unittest.TestCase):
    def test_build_coordination_rows_has_four_sections(self) -> None:
        rows = build_coordination_rows()
        self.assertEqual(len(rows), 4)
        section_ids = {row["section_id"] for row in rows}
        self.assertIn("meeteval_closure", section_ids)
        self.assertIn("cascade_pareto", section_ids)

    def test_build_fill_row_marks_writeback_filled(self) -> None:
        row = build_fill_row(build_coordination_rows())
        self.assertEqual(row["fill_status"], "writeback_filled")
        self.assertEqual(row["execution_receipt_status"], "cascade_coordination_writeback_complete")

    def test_run_coordination_writeback_requires_meeteval_closure(self) -> None:
        with patch(
            "src.cascade_frontier_coordination_writeback.load_json_dict",
            side_effect=[
                {"readiness_status": "receipt_ready_to_fill"},
                {"coordination_state": "all_ready"},
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_coordination_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
