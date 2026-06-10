from __future__ import annotations

import unittest
import unittest.mock

from src.adaptive_router import parse_args as adaptive_router_parse_args
from src.analyze_cer_errors import parse_args as analyze_cer_parse_args
from src.evaluate_cer import parse_args as evaluate_cer_parse_args
from src.generate_synthetic_overlap import parse_args as generate_synthetic_overlap_parse_args
from src.evaluate_cpcer_lite import parse_args as evaluate_cpcer_parse_args
from src.evaluate_error_types import parse_args as evaluate_error_types_parse_args
from src.evaluate_speaker_cer import parse_args as evaluate_speaker_cer_parse_args
from src.plot_results import parse_args as plot_results_parse_args
from src.router_ablation import parse_args as router_ablation_parse_args
from src.risk_aware_selector import parse_args as risk_aware_parse_args


class ModuleParseArgsSmokeTest(unittest.TestCase):
    def test_evaluate_cer_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["evaluate_cer", "--case", "all"]):
            self.assertEqual(evaluate_cer_parse_args().case, "all")

    def test_analyze_cer_errors_parse_args(self) -> None:
        with unittest.mock.patch(
            "sys.argv",
            ["analyze_cer_errors", "--case", "LightOverlap", "--method", "mixed_whisper"],
        ):
            args = analyze_cer_parse_args()
            self.assertEqual(args.case, "LightOverlap")
            self.assertEqual(args.method, "mixed_whisper")

    def test_evaluate_error_types_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["evaluate_error_types", "--case", "NoOverlap"]):
            self.assertEqual(evaluate_error_types_parse_args().case, "NoOverlap")

    def test_evaluate_cpcer_lite_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["evaluate_cpcer_lite", "--case", "all"]):
            self.assertEqual(evaluate_cpcer_parse_args().case, "all")

    def test_evaluate_speaker_cer_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["evaluate_speaker_cer", "--case", "LightOverlap"]):
            self.assertEqual(evaluate_speaker_cer_parse_args().case, "LightOverlap")

    def test_router_ablation_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["router_ablation", "--dataset", "synthetic_overlap_v2"]):
            self.assertEqual(router_ablation_parse_args().dataset, "synthetic_overlap_v2")

    def test_risk_aware_selector_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["risk_aware_selector", "--case", "all"]):
            self.assertEqual(risk_aware_parse_args().case, "all")

    def test_plot_results_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["plot_results"]):
            self.assertIsNotNone(plot_results_parse_args())

    def test_adaptive_router_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["adaptive_router"]):
            self.assertIsNotNone(adaptive_router_parse_args())


if __name__ == "__main__":
    unittest.main()
