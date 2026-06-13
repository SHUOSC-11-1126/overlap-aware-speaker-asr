from __future__ import annotations

import unittest
import unittest.mock

from src.analyze_cer_errors import parse_args as analyze_cer_parse_args
from src.build_synthetic_references import parse_args as build_synthetic_references_parse_args
from src.compare_mixed_vs_separated import parse_args as compare_mixed_vs_separated_parse_args
from src.compute_aware_cascade import parse_args as compute_aware_cascade_parse_args
from src.evaluate_cer import parse_args as evaluate_cer_parse_args
from src.evaluate_synthetic_benchmark import parse_args as evaluate_synthetic_benchmark_parse_args
from src.evaluate_synthetic_routing import parse_args as evaluate_synthetic_routing_parse_args
from src.meeteval_cpwer_bridge import parse_args as meeteval_cpwer_bridge_parse_args
from src.merge_speaker_tracks import parse_args as merge_speaker_tracks_parse_args
from src.prepare_reference_bundle import parse_args as prepare_reference_bundle_parse_args
from src.generate_synthetic_overlap import parse_args as generate_synthetic_overlap_parse_args
from src.generate_synthetic_split import parse_args as generate_synthetic_split_parse_args
from src.postprocess_transcript import parse_args as postprocess_transcript_parse_args
from src.evaluate_cpcer_lite import parse_args as evaluate_cpcer_parse_args
from src.evaluate_error_types import parse_args as evaluate_error_types_parse_args
from src.evaluate_speaker_cer import parse_args as evaluate_speaker_cer_parse_args
from src.plot_results import parse_args as plot_results_parse_args
from src.router_ablation import parse_args as router_ablation_parse_args
from src.risk_aware_selector import parse_args as risk_aware_parse_args
from src.run_experiment import parse_args as run_experiment_parse_args
from src.summarize_results import parse_args as summarize_results_parse_args
from src.transcribe_snippets import parse_args as transcribe_snippets_parse_args
from src.transcribe_whisper import parse_args as transcribe_whisper_parse_args


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

    def test_generate_synthetic_overlap_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["generate_synthetic_overlap", "--num-per-tier", "3"]):
            self.assertEqual(generate_synthetic_overlap_parse_args().num_per_tier, 3)

    def test_generate_synthetic_split_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["generate_synthetic_split", "--num-per-tier", "12"]):
            self.assertEqual(generate_synthetic_split_parse_args().num_per_tier, 12)

    def test_postprocess_transcript_parse_args(self) -> None:
        with unittest.mock.patch(
            "sys.argv",
            ["postprocess_transcript", "--case", "NoOverlap", "--method", "duplicate_suppression"],
        ):
            args = postprocess_transcript_parse_args()
            self.assertEqual(args.case, "NoOverlap")
            self.assertEqual(args.method, "duplicate_suppression")
            self.assertFalse(args.overwrite)

    def test_transcribe_whisper_parse_args(self) -> None:
        with unittest.mock.patch(
            "sys.argv",
            ["transcribe_whisper", "--case", "NoOverlap", "--mode", "mixed", "--overwrite"],
        ):
            args = transcribe_whisper_parse_args()
            self.assertEqual(args.case, "NoOverlap")
            self.assertEqual(args.mode, "mixed")
            self.assertTrue(args.overwrite)

    def test_compare_mixed_vs_separated_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["compare_mixed_vs_separated", "--case", "all"]):
            self.assertEqual(compare_mixed_vs_separated_parse_args().case, "all")

    def test_evaluate_synthetic_routing_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["evaluate_synthetic_routing", "--dataset", "synthetic_overlap_v2"]):
            self.assertEqual(evaluate_synthetic_routing_parse_args().dataset, "synthetic_overlap_v2")

    def test_evaluate_synthetic_benchmark_parse_args(self) -> None:
        with unittest.mock.patch(
            "sys.argv",
            ["evaluate_synthetic_benchmark", "--case", "SyntheticNoOverlap_01", "--dataset", "synthetic_overlap"],
        ):
            args = evaluate_synthetic_benchmark_parse_args()
            self.assertEqual(args.case, "SyntheticNoOverlap_01")
            self.assertEqual(args.dataset, "synthetic_overlap")

    def test_build_synthetic_references_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["build_synthetic_references", "--dataset", "synthetic_overlap"]):
            self.assertEqual(build_synthetic_references_parse_args().dataset, "synthetic_overlap")

    def test_compute_aware_cascade_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["compute_aware_cascade", "--dataset", "synthetic_split"]):
            self.assertEqual(compute_aware_cascade_parse_args().dataset, "synthetic_split")

    def test_run_experiment_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["run_experiment", "--stage", "compare", "--overwrite"]):
            args = run_experiment_parse_args()
            self.assertEqual(args.stage, "compare")
            self.assertTrue(args.overwrite)

    def test_merge_speaker_tracks_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["merge_speaker_tracks", "--case", "NoOverlap"]):
            self.assertEqual(merge_speaker_tracks_parse_args().case, "NoOverlap")

    def test_prepare_reference_bundle_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["prepare_reference_bundle", "--case", "NoOverlap"]):
            self.assertEqual(prepare_reference_bundle_parse_args().case, "NoOverlap")

    def test_transcribe_snippets_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["transcribe_snippets", "--overwrite"]):
            self.assertTrue(transcribe_snippets_parse_args().overwrite)

    def test_summarize_results_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["summarize_results"]):
            self.assertIsNotNone(summarize_results_parse_args())

    def test_meeteval_cpwer_bridge_parse_args(self) -> None:
        with unittest.mock.patch("sys.argv", ["meeteval_cpwer_bridge", "--case", "all"]):
            self.assertEqual(meeteval_cpwer_bridge_parse_args().case, "all")


if __name__ == "__main__":
    unittest.main()
