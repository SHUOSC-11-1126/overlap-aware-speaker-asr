from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from src.config import PROJECT_ROOT
from src.prepare_reference_bundle import build_bundle


class PrepareReferenceBundleBuildBundleTest(unittest.TestCase):
    def test_build_bundle_reports_missing_files(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
            tmp_path = Path(tmp_dir)
            config = {
                "paths": {
                    "mixed_audio_dir": tmp_path.relative_to(PROJECT_ROOT).as_posix(),
                    "separated_audio_dir": tmp_path.relative_to(PROJECT_ROOT).as_posix(),
                    "results_dir": tmp_path.relative_to(PROJECT_ROOT).as_posix(),
                }
            }
            with mock.patch("src.prepare_reference_bundle.PROJECT_ROOT", tmp_path):
                output_zip, missing = build_bundle("MissingCase", config)
        self.assertGreater(len(missing), 0)
        self.assertFalse(output_zip.exists())

    def test_build_bundle_creates_zip_when_files_exist(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
            tmp_path = Path(tmp_dir)
            mixed = tmp_path / "mixed"
            separated = tmp_path / "separated"
            results = tmp_path / "results"
            for folder in (mixed, separated, results / "transcripts_raw", results / "transcripts_speaker"):
                folder.mkdir(parents=True)
            case_id = "BundleCase"
            (mixed / f"{case_id}.wav").write_bytes(b"wav")
            (separated / f"{case_id}_spk1.wav").write_bytes(b"wav")
            (separated / f"{case_id}_spk2.wav").write_bytes(b"wav")
            (results / "transcripts_raw" / f"{case_id}_mixed_whisper.json").write_text("{}", encoding="utf-8")
            (results / "transcripts_raw" / f"{case_id}_spk1_whisper.json").write_text("{}", encoding="utf-8")
            (results / "transcripts_raw" / f"{case_id}_spk2_whisper.json").write_text("{}", encoding="utf-8")
            (results / "transcripts_speaker" / f"{case_id}_separated_speaker_transcript.json").write_text(
                "{}", encoding="utf-8"
            )
            config = {
                "paths": {
                    "mixed_audio_dir": mixed.relative_to(tmp_path).as_posix(),
                    "separated_audio_dir": separated.relative_to(tmp_path).as_posix(),
                    "results_dir": results.relative_to(tmp_path).as_posix(),
                }
            }
            with mock.patch("src.prepare_reference_bundle.PROJECT_ROOT", tmp_path):
                output_zip, missing = build_bundle(case_id, config)
                self.assertEqual(missing, [])
                self.assertTrue(output_zip.is_file())
                with zipfile.ZipFile(output_zip) as archive:
                    self.assertGreater(len(archive.namelist()), 0)


if __name__ == "__main__":
    unittest.main()
