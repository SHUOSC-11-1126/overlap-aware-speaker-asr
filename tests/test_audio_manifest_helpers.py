from __future__ import annotations

import tempfile
import unittest
import wave
from pathlib import Path

from src.audio_manifest import add_audio_row, build_manifest, read_wav_info, write_manifest
from src.config import load_config


class AudioManifestHelpersTest(unittest.TestCase):
    def test_read_wav_info_reads_duration_and_channels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            wav_path = Path(tmp_dir) / "demo.wav"
            with wave.open(str(wav_path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(16000)
                handle.writeframes(b"\x00\x00" * 16000)

            info = read_wav_info(wav_path)
            self.assertEqual(info["sample_rate"], 16000)
            self.assertEqual(info["channels"], 1)
            self.assertEqual(info["duration_sec"], 1.0)

    def test_write_manifest_writes_csv_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "manifest.csv"
            write_manifest(
                [
                    {
                        "case_id": "Demo",
                        "audio_type": "mixed",
                        "path": "demo.wav",
                        "duration_sec": 1.0,
                        "sample_rate": 16000,
                        "channels": 1,
                        "overlap_level": 0,
                    }
                ],
                output_path,
            )
            content = output_path.read_text(encoding="utf-8")
            self.assertIn("case_id", content)
            self.assertIn("Demo", content)

    def test_build_manifest_includes_gold_case_audio_rows(self) -> None:
        config = load_config()
        rows = build_manifest(config)
        case_ids = {row["case_id"] for row in rows}
        self.assertIn("NoOverlap", case_ids)
        audio_types = {row["audio_type"] for row in rows if row["case_id"] == "NoOverlap"}
        self.assertIn("mixed", audio_types)
        self.assertIn("separated_spk1", audio_types)

    def test_add_audio_row_appends_manifest_entry_from_wav(self) -> None:
        from src.config import PROJECT_ROOT

        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
            tmp_path = Path(tmp_dir)
            wav_path = tmp_path / "demo.wav"
            with wave.open(str(wav_path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(16000)
                handle.writeframes(b"\x00\x00" * 8000)

            rows: list[dict] = []
            rel_path = wav_path.relative_to(PROJECT_ROOT)
            add_audio_row(rows, "Demo", "mixed", rel_path, overlap_level=0)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["case_id"], "Demo")
            self.assertEqual(rows[0]["duration_sec"], 0.5)

    def test_add_audio_row_raises_for_missing_file(self) -> None:
        rows: list[dict] = []
        with self.assertRaises(FileNotFoundError):
            add_audio_row(rows, "Demo", "mixed", Path("nonexistent/demo.wav"), overlap_level=0)
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
