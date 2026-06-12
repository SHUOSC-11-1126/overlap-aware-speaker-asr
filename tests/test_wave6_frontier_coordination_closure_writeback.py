from __future__ import annotations

import unittest
from unittest.mock import patch

from src.wave6_frontier_coordination_closure_writeback import (
    build_closure_rows,
    build_fill_row,
    run_closure_writeback,
)


class Wave6FrontierCoordinationClosureWritebackTest(unittest.TestCase):
    def test_build_closure_rows_has_five_sections(self) -> None:
        rows = build_closure_rows()
        self.assertEqual(len(rows), 5)
        self.assertIn("wave6_next_boundary", {row["section_id"] for row in rows})

    def test_build_fill_row_marks_closure_complete(self) -> None:
        row = build_fill_row(build_closure_rows())
        self.assertEqual(row["execution_receipt_status"], "wave6_coordination_closure_complete")

    def test_run_closure_writeback_requires_demo_wave5(self) -> None:
        with patch(
            "src.wave6_frontier_coordination_closure_writeback.load_json_dict",
            side_effect=[
                {"fill_status": "pending"},
                {"execution_status": "phase_coordination_writeback_complete"},
                {"execution_status": "cascade_coordination_writeback_complete"},
                {"execution_receipt_status": "character_level_cpwer_receipt_fill_complete"},
                {"coordination_state": "all_ready"},
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_closure_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
