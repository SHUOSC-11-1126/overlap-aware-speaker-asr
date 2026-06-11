from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from src.evaluate_synthetic_routing import (
    PERFORMANCE_COLUMNS,
    SPLIT_DECISION_COLUMNS,
    STRATEGIES,
    build_decision_row,
    build_decisions,
    write_outputs,
)


class EvaluateSyntheticRoutingBuildDecisionRowTest(unittest.TestCase):
    def test_build_decision_row_uses_repo_synthetic_overlap_sample(self) -> None:
        row = {
            "sample_id": "SyntheticNoOverlap_01",
            "tier": "SyntheticNoOverlap",
            "overlap_level_numeric": 0,
        }
        decision = build_decision_row(row, {}, "synthetic_overlap")
        self.assertEqual(decision["sample_id"], "SyntheticNoOverlap_01")
        self.assertEqual(decision["tier"], "SyntheticNoOverlap")
        self.assertIn(decision["selected_method"], {"mixed_whisper", "separated_whisper", "separated_whisper_cleaned"})
        self.assertTrue(decision["decision_rule"])
        self.assertGreater(decision["mixed_text_length"], 0)

    def test_build_decisions_expands_strategies_for_manifest_row(self) -> None:
        manifest = [
            {
                "sample_id": "SyntheticNoOverlap_01",
                "tier": "SyntheticNoOverlap",
                "overlap_level_numeric": 0,
            }
        ]
        decisions = build_decisions(manifest, {}, "synthetic_overlap")
        self.assertEqual(len(decisions), len(STRATEGIES))
        strategies = {row["strategy"] for row in decisions}
        self.assertEqual(strategies, set(STRATEGIES))

    def test_write_outputs_writes_csv_json_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            paths = {
                "decisions_csv": base / "decisions.csv",
                "decisions_json": base / "decisions.json",
                "performance_csv": base / "performance.csv",
                "performance_json": base / "performance.json",
                "summary_md": base / "summary.md",
            }
            decisions: list[dict[str, Any]] = [
                {
                    "sample_id": "s1",
                    "tier": "SyntheticNoOverlap",
                    "split": "train",
                    "strategy": "v1_overlap_only",
                    "selected_method": "separated_whisper",
                    "decision_rule": "overlap routing",
                    "mixed_segments_count": 2,
                    "separated_segments_count": 2,
                    "cleaned_segments_count": 2,
                    "mixed_text_length": 10,
                    "separated_text_length": 10,
                    "cleaned_text_length": 10,
                    "text_length_ratio": 1.0,
                    "mixed_runtime_sec": 1.0,
                    "separated_runtime_sec": 2.0,
                    "cleaned_runtime_sec": 2.0,
                    "runtime_ratio": 2.0,
                    "duplicate_removed_count": 0,
                    "notes": "test",
                }
            ]
            performance = [
                {"scope": "ALL", "strategy": "v1_overlap_only", "average_cer": 0.1, "sample_count": 1}
            ]
            write_outputs(paths, decisions, performance)

            with paths["decisions_csv"].open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["sample_id"], "s1")
            self.assertEqual(list(rows[0].keys()), SPLIT_DECISION_COLUMNS)

            payload = json.loads(paths["decisions_json"].read_text(encoding="utf-8"))
            self.assertEqual(len(payload), 1)

            with paths["performance_csv"].open(encoding="utf-8-sig", newline="") as handle:
                perf_rows = list(csv.DictReader(handle))
            self.assertEqual(list(perf_rows[0].keys()), PERFORMANCE_COLUMNS)

            summary = paths["summary_md"].read_text(encoding="utf-8")
            self.assertIn("Synthetic Routing Stability Summary", summary)
            self.assertIn("v1_overlap_only", summary)


if __name__ == "__main__":
    unittest.main()
