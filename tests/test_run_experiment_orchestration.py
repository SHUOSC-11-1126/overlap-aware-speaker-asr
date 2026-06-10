from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.run_experiment import main, run


class RunExperimentOrchestrationTest(unittest.TestCase):
    @patch("src.run_experiment.subprocess.run")
    def test_run_invokes_python_module_with_extra_args(self, mock_run: MagicMock) -> None:
        run("src.compare_mixed_vs_separated", "--case", "all")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("-m", cmd)
        self.assertEqual(cmd[cmd.index("-m") + 1], "src.compare_mixed_vs_separated")
        self.assertIn("--case", cmd)
        self.assertIn("all", cmd)

    @patch("src.run_experiment.run")
    @patch("sys.argv", ["run_experiment", "--stage", "compare"])
    def test_main_compare_stage_calls_compare_module(self, mock_run: MagicMock) -> None:
        main()
        mock_run.assert_called_once_with("src.compare_mixed_vs_separated", "--case", "all")

    @patch("src.run_experiment.run")
    @patch("sys.argv", ["run_experiment", "--stage", "separated", "--overwrite"])
    def test_main_separated_stage_chains_transcribe_and_merge(self, mock_run: MagicMock) -> None:
        main()
        self.assertEqual(mock_run.call_count, 2)
        mock_run.assert_any_call(
            "src.transcribe_whisper",
            "--case",
            "all",
            "--overwrite",
            "--mode",
            "separated",
        )
        mock_run.assert_any_call("src.merge_speaker_tracks", "--case", "all", "--overwrite")


if __name__ == "__main__":
    unittest.main()
