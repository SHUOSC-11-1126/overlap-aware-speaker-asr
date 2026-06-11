from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.build_synthetic_references import main


class BuildSyntheticReferencesMainTest(unittest.TestCase):
    def test_main_updates_manifest_with_silver_reference_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            tables_dir = root / "results" / "tables"
            snippet_dir = root / "results" / "snippet_transcripts"
            reference_dir = root / "resources" / "synthetic_overlap" / "references"
            tables_dir.mkdir(parents=True)
            snippet_dir.mkdir(parents=True)
            reference_dir.mkdir(parents=True)

            manifest_path = tables_dir / "synthetic_manifest.csv"
            with manifest_path.open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "sample_id",
                        "tier",
                        "split",
                        "con_source",
                        "pro_source",
                        "overlap_ratio",
                        "reference_path",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "sample_id": "FixtureSample",
                        "tier": "SyntheticNoOverlap",
                        "split": "dev",
                        "con_source": "con.wav",
                        "pro_source": "pro.wav",
                        "overlap_ratio": "0.0",
                        "reference_path": "resources/synthetic_overlap/references/placeholder.json",
                    }
                )

            for snippet in ("con", "pro"):
                payload = {"text": f"{snippet}-text", "transcript_path": f"results/snippet_transcripts/{snippet}_whisper.json"}
                (snippet_dir / f"{snippet}_whisper.json").write_text(json.dumps(payload), encoding="utf-8")

            with patch("src.build_synthetic_references.PROJECT_ROOT", root), patch(
                "sys.argv", ["build_synthetic_references", "--dataset", "synthetic_overlap"]
            ):
                main()

            with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["reference_status"], "silver_reference")
            self.assertTrue(rows[0]["silver_reference_path"].endswith("FixtureSample_silver_reference.json"))
            self.assertTrue((reference_dir / "FixtureSample_silver_reference.json").exists())


if __name__ == "__main__":
    unittest.main()
