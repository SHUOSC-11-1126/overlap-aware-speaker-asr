from __future__ import annotations

import unittest
from unittest.mock import patch

from src.separation_phase_coordination_writeback import (
    build_coordination_rows,
    build_fill_row,
    run_coordination_writeback,
)


class SeparationPhaseCoordinationWritebackTest(unittest.TestCase):
    def test_build_coordination_rows_has_four_sections(self) -> None:
        rows = build_coordination_rows()
        self.assertEqual(len(rows), 4)
        self.assertIn("phase_gold_anchors", {row["section_id"] for row in rows})

    def test_build_fill_row_marks_phase_coordination_complete(self) -> None:
        row = build_fill_row(build_coordination_rows())
        self.assertEqual(row["execution_receipt_status"], "phase_coordination_writeback_complete")

    def test_run_coordination_writeback_requires_cascade_receipt(self) -> None:
        with patch(
            "src.separation_phase_coordination_writeback.load_json_dict",
            return_value={"execution_status": "pending"},
        ):
            with self.assertRaises(RuntimeError):
                run_coordination_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
