from __future__ import annotations

import unittest
from pathlib import Path

from src.evaluate_synthetic_benchmark import (
    cleaned_transcript_path,
    dataset_paths,
    output_columns,
    select_rows,
    speaker_transcript_path,
    transcript_path,
)


class EvaluateSyntheticBenchmarkHelpersTest(unittest.TestCase):
    def test_dataset_paths_returns_synthetic_overlap_artifacts(self) -> None:
        paths = dataset_paths("synthetic_overlap")
        self.assertTrue(str(paths["manifest"]).endswith("synthetic_manifest.csv"))

    def test_transcript_path_builders_use_expected_suffixes(self) -> None:
        directory = Path("results/synthetic_transcripts_raw")
        self.assertEqual(
            transcript_path("sample_001", "mixed", directory).name,
            "sample_001_mixed_whisper.json",
        )
        self.assertEqual(
            speaker_transcript_path("sample_001", directory).name,
            "sample_001_separated_speaker_transcript.json",
        )
        self.assertEqual(
            cleaned_transcript_path("sample_001", directory).name,
            "sample_001_separated_speaker_transcript_cleaned.json",
        )

    def test_select_rows_filters_by_sample_id(self) -> None:
        rows = [{"sample_id": "a"}, {"sample_id": "b"}]
        self.assertEqual(select_rows(rows, "a"), [{"sample_id": "a"}])
        with self.assertRaises(ValueError):
            select_rows(rows, "missing")

    def test_output_columns_includes_split_when_present(self) -> None:
        base = output_columns([{"sample_id": "a"}])
        with_split = output_columns([{"sample_id": "a", "split": "dev"}])
        self.assertNotIn("split", base)
        self.assertIn("split", with_split)


if __name__ == "__main__":
    unittest.main()
