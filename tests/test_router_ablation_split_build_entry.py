from __future__ import annotations

import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from src.router_ablation_split import build_entry


class RouterAblationSplitBuildEntryTest(unittest.TestCase):
    def test_build_entry_computes_lengths_and_runtime_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            raw_dir = base / "raw"
            speaker_dir = base / "speaker"
            cleaned_dir = base / "cleaned"
            for directory in (raw_dir, speaker_dir, cleaned_dir):
                directory.mkdir(parents=True, exist_ok=True)

            sample_id = "sample_001"
            (raw_dir / f"{sample_id}_mixed_whisper.json").write_text(
                json.dumps({"text": "abcd", "segments": [{"text": "abcd"}], "runtime_sec": 2.0}),
                encoding="utf-8",
            )
            (speaker_dir / f"{sample_id}_separated_speaker_transcript.json").write_text(
                json.dumps(
                    {
                        "full_text": "abcdef",
                        "segments": [{"text": "ab"}, {"text": "ab"}],
                        "runtime_sec_total": 4.0,
                    }
                ),
                encoding="utf-8",
            )
            (cleaned_dir / f"{sample_id}_separated_speaker_transcript_cleaned.json").write_text(
                json.dumps({"cleaned_full_text": "ab", "cleaned_segments": [{"text": "ab"}], "removed_count": 1}),
                encoding="utf-8",
            )

            paths = {
                "raw_dir": raw_dir,
                "speaker_dir": speaker_dir,
                "cleaned_dir": cleaned_dir,
            }
            manifest_row = {
                "sample_id": sample_id,
                "tier": "SyntheticNoOverlap",
                "split": "dev",
                "overlap_level_numeric": 0,
            }
            with unittest.mock.patch("src.router_ablation_split.dataset_paths", return_value=paths):
                entry = build_entry(manifest_row, {})

        self.assertEqual(entry["mixed_text_length"], 4)
        self.assertEqual(entry["separated_text_length"], 6)
        self.assertEqual(entry["runtime_ratio"], 2.0)
        self.assertEqual(entry["repetition_count"], 1)
        self.assertEqual(entry["duplicate_removed_count"], 1)


if __name__ == "__main__":
    unittest.main()
