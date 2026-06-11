from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from typing import Any

from src.router_ablation_split import (
    DECISION_COLUMNS,
    PERFORMANCE_COLUMNS,
    build_decisions,
    build_performance,
    write_outputs,
)


def _entry(sample_id: str = "s1", tier: str = "SyntheticNoOverlap", split: str = "dev") -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "tier": tier,
        "split": split,
        "overlap_level": 0,
        "mixed_text_length": 100,
        "separated_text_length": 110,
        "cleaned_text_length": 105,
        "text_length_ratio": 1.1,
        "repetition_count": 0,
        "duplicate_removed_count": 0,
        "mixed_segments_count": 2,
        "separated_segments_count": 2,
        "cleaned_segments_count": 2,
        "mixed_runtime_sec": 1.0,
        "separated_runtime_sec": 2.0,
        "cleaned_runtime_sec": 2.0,
        "runtime_ratio": 2.0,
        "cleaned_closer_to_mixed": True,
        "notes": "test",
        "mixed_text": "mixed",
        "separated_text": "separated",
        "cleaned_text": "cleaned",
    }


class RouterAblationSplitWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_writes_csv_json_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            paths = {
                "decisions_csv": base / "decisions.csv",
                "decisions_json": base / "decisions.json",
                "summary_csv": base / "summary.csv",
                "summary_json": base / "summary.json",
                "summary_md": base / "summary.md",
            }
            decisions = build_decisions([_entry()])
            performance = build_performance({("s1", "mixed_whisper"): 0.2}, [_entry()])
            write_outputs(paths, decisions, performance)

            for path in paths.values():
                self.assertTrue(path.exists())
            with paths["decisions_csv"].open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(list(rows[0].keys()), DECISION_COLUMNS)
            with paths["summary_csv"].open(encoding="utf-8-sig", newline="") as handle:
                perf_rows = list(csv.DictReader(handle))
            self.assertEqual(list(perf_rows[0].keys()), PERFORMANCE_COLUMNS)
            self.assertIn("Router Ablation Summary", paths["summary_md"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
