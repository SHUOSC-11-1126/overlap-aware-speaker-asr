from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from src import config as config_module
from src.config import PROJECT_ROOT, get_audio_cases, load_config, resolve_path


class ConfigTest(unittest.TestCase):
    def test_resolve_path_joins_under_project_root(self) -> None:
        resolved = resolve_path("configs", "config.yaml")
        self.assertEqual(resolved, str(PROJECT_ROOT / "configs" / "config.yaml"))

    def test_load_config_reads_default_yaml(self) -> None:
        config = load_config()
        self.assertIn("audio_cases", config)
        self.assertIsInstance(config["audio_cases"], list)
        self.assertGreater(len(config["audio_cases"]), 0)

    def test_load_config_raises_for_missing_file(self) -> None:
        missing = PROJECT_ROOT / "configs" / "__missing_config__.yaml"
        with self.assertRaises(FileNotFoundError) as ctx:
            load_config(str(missing))
        self.assertIn("Missing config file", str(ctx.exception))

    def test_load_config_raises_for_malformed_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            bad_path = Path(tmp_dir) / "bad.yaml"
            bad_path.write_text("audio_cases: [unclosed", encoding="utf-8")
            with self.assertRaises(Exception):
                load_config(str(bad_path))

    def test_load_config_accepts_absolute_path(self) -> None:
        config_path = PROJECT_ROOT / "configs" / "config.yaml"
        config = load_config(str(config_path))
        self.assertIn("paths", config)

    def test_get_audio_cases_returns_case_list(self) -> None:
        config = load_config()
        cases = get_audio_cases(config)
        self.assertTrue(all("id" in case for case in cases))

    def test_main_prints_configured_audio_cases(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            config_module.main()
        output = buffer.getvalue()
        self.assertIn("NoOverlap", output)
        self.assertIn("overlap_level=", output)


if __name__ == "__main__":
    unittest.main()
