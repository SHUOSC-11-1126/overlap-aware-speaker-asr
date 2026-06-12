from __future__ import annotations

import unittest
from unittest.mock import patch

from src.cascade_benchmark_manifest_coordination_writeback import (
    build_coordination_rows,
    build_fill_row,
    run_coordination_writeback,
)


class CascadeBenchmarkManifestCoordinationWritebackTest(unittest.TestCase):
    def test_build_coordination_rows_has_four_sections(self) -> None:
        self.assertEqual(len(build_coordination_rows()), 4)

    def test_build_fill_row_records_manifest_blocker(self) -> None:
        row = build_fill_row(build_coordination_rows(), "4")
        self.assertEqual(row["execution_receipt_status"], "cascade_benchmark_manifest_coordination_complete")
        self.assertEqual(row["blocker"], "controlled_benchmark_timing_pending")

    def test_run_coordination_writeback_requires_wave7_closure(self) -> None:
        with patch(
            "src.cascade_benchmark_manifest_coordination_writeback.load_json_dict",
            return_value={"execution_status": "pending"},
        ):
            with self.assertRaises(RuntimeError):
                run_coordination_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
