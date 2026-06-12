from __future__ import annotations

import unittest
from unittest.mock import patch

from src.cascade_benchmark_phase5_gate_coordination_writeback import (
    build_coordination_rows,
    build_fill_row,
    run_coordination_writeback,
)


class CascadeBenchmarkPhase5GateCoordinationWritebackTest(unittest.TestCase):
    def test_build_coordination_rows_has_five_sections(self) -> None:
        self.assertEqual(len(build_coordination_rows()), 5)

    def test_build_fill_row_records_phase5_gate(self) -> None:
        row = build_fill_row(build_coordination_rows())
        self.assertEqual(row["phase5_gate_id"], "phase5_cross_dataset_refresh")
        self.assertEqual(row["execution_receipt_status"], "cascade_benchmark_phase5_gate_coordination_complete")

    def test_run_coordination_writeback_requires_wave14_closure(self) -> None:
        with patch(
            "src.cascade_benchmark_phase5_gate_coordination_writeback.load_json_dict",
            side_effect=[
                {"execution_status": "pending"},
                {"execution_status": "cascade_benchmark_phase4_gate_coordination_complete"},
                {"execution_status": "meeteval_official_narrow_dry_run_coordination_complete"},
                {
                    "fill_status": "writeback_filled",
                    "storyboard_receipt_status": "wave14_presentation_extension_complete",
                },
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_coordination_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
