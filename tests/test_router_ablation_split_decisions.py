from __future__ import annotations

import csv
import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

from src.router_ablation_split import (
    DECISION_COLUMNS,
    PERFORMANCE_COLUMNS,
    STRATEGIES,
    build_decisions,
    build_performance,
    load_cleaned_rows,
    load_cer_lookup,
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


class RouterAblationSplitDecisionsTest(unittest.TestCase):
    def test_build_decisions_expands_strategies_per_entry(self) -> None:
        decisions = build_decisions([_entry()])
        self.assertEqual(len(decisions), len(STRATEGIES))
        self.assertEqual({row["strategy"] for row in decisions}, set(STRATEGIES))

    def test_load_cer_lookup_indexes_sample_method_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "cer.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["sample_id", "method", "cer"])
                writer.writeheader()
                writer.writerow({"sample_id": "s1", "method": "mixed_whisper", "cer": "0.12"})
            with unittest.mock.patch("src.router_ablation_split.dataset_paths", return_value={"cer": csv_path}):
                lookup = load_cer_lookup()
        self.assertEqual(lookup[("s1", "mixed_whisper")], 0.12)

    def test_build_performance_emits_scope_rows_with_gap_to_oracle(self) -> None:
        entries = [_entry()]
        cer_lookup = {
            ("s1", "mixed_whisper"): 0.3,
            ("s1", "separated_whisper"): 0.1,
            ("s1", "separated_whisper_cleaned"): 0.2,
        }
        performance = build_performance(cer_lookup, entries)
        self.assertTrue(any(row["scope"] == "ALL" for row in performance))
        self.assertIn("gap_to_oracle", performance[0])

    def test_load_cleaned_rows_indexes_payloads_and_skips_bad_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cleaned_dir = Path(tmp_dir)
            good = cleaned_dir / "s1_separated_speaker_transcript_cleaned.json"
            good.write_text(json.dumps({"sample_id": "s1", "cleaned_full_text": "ok"}), encoding="utf-8")
            bad = cleaned_dir / "bad_separated_speaker_transcript_cleaned.json"
            bad.write_text("{not json", encoding="utf-8")
            with unittest.mock.patch(
                "src.router_ablation_split.dataset_paths",
                return_value={"cleaned_dir": cleaned_dir},
            ):
                rows = load_cleaned_rows()
        self.assertEqual(rows["s1"]["cleaned_full_text"], "ok")
        self.assertNotIn("bad", rows)

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
            with paths["decisions_csv"].open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(list(rows[0].keys()), DECISION_COLUMNS)
            with paths["summary_csv"].open(encoding="utf-8-sig", newline="") as handle:
                perf_rows = list(csv.DictReader(handle))
            self.assertEqual(list(perf_rows[0].keys()), PERFORMANCE_COLUMNS)
            summary = paths["summary_md"].read_text(encoding="utf-8")
            self.assertIn("Router Ablation Summary", summary)


if __name__ == "__main__":
    unittest.main()
