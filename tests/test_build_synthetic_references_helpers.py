from __future__ import annotations

import unittest

from src.build_synthetic_references import (
    TIER_TO_LEVEL,
    build_turns,
    dataset_paths,
    read_csv_rows,
    read_json,
    snippet_transcript_path,
)
from src.config import PROJECT_ROOT


class BuildSyntheticReferencesHelpersTest(unittest.TestCase):
    def test_tier_to_level_maps_synthetic_tiers(self) -> None:
        self.assertEqual(TIER_TO_LEVEL["SyntheticNoOverlap"], 0)
        self.assertEqual(TIER_TO_LEVEL["SyntheticHeavyOverlap"], 3)

    def test_snippet_transcript_path_under_results(self) -> None:
        path = snippet_transcript_path("demo_snippet")
        self.assertEqual(
            path,
            PROJECT_ROOT / "results" / "snippet_transcripts" / "demo_snippet_whisper.json",
        )

    def test_build_turns_assigns_speakers_and_order(self) -> None:
        turns = build_turns("con.wav", "pro.wav", "反方", "正方")
        self.assertEqual(turns[0]["speaker"], "SPEAKER_1")
        self.assertEqual(turns[1]["speaker"], "SPEAKER_2")
        self.assertEqual(turns[0]["text"], "反方")

    def test_dataset_paths_returns_v2_split_artifacts(self) -> None:
        manifest, reference_dir, label = dataset_paths("synthetic_overlap_v2")
        self.assertTrue(str(manifest).endswith("synthetic_split_manifest.csv"))
        self.assertEqual(label, "synthetic_overlap_v2")
        self.assertIn("synthetic_overlap_v2", reference_dir.as_posix())

    def test_dataset_paths_returns_default_overlap_manifest(self) -> None:
        manifest, _, label = dataset_paths("synthetic_overlap")
        self.assertTrue(str(manifest).endswith("synthetic_manifest.csv"))
        self.assertEqual(label, "synthetic_overlap")

    def test_dataset_paths_rejects_unknown_dataset(self) -> None:
        with self.assertRaises(ValueError):
            dataset_paths("unknown_dataset")

    def test_read_csv_rows_raises_for_missing_table(self) -> None:
        missing = PROJECT_ROOT / "results" / "tables" / "__missing_manifest__.csv"
        with self.assertRaises(FileNotFoundError):
            read_csv_rows(missing)

    def test_read_json_raises_for_missing_file(self) -> None:
        missing = PROJECT_ROOT / "results" / "tables" / "__missing__.json"
        with self.assertRaises(FileNotFoundError):
            read_json(missing)


if __name__ == "__main__":
    unittest.main()
