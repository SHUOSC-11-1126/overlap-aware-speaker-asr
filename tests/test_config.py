from __future__ import annotations

import unittest
from pathlib import Path

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

    def test_load_config_accepts_absolute_path(self) -> None:
        config_path = PROJECT_ROOT / "configs" / "config.yaml"
        config = load_config(str(config_path))
        self.assertIn("paths", config)

    def test_get_audio_cases_returns_case_list(self) -> None:
        config = load_config()
        cases = get_audio_cases(config)
        self.assertTrue(all("id" in case for case in cases))


if __name__ == "__main__":
    unittest.main()
