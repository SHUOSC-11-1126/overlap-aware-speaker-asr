from __future__ import annotations

import math
import unittest

from src.separation_phase_boundary import (
    bootstrap_crossover_ci,
    build_boundary_metadata,
    build_dense_trend_rows,
    compute_crossover_boundary,
    lowess_smooth,
    tricube_weights,
)


class TricubeWeightsTest(unittest.TestCase):
    def test_returns_weights_for_points_within_bandwidth(self) -> None:
        distances = [0.0, 0.3, 0.5, 0.9, 1.2]
        w = tricube_weights(distances, bandwidth=1.0)
        self.assertAlmostEqual(w[0], 1.0, places=4)  # distance 0 -> weight 1
        self.assertGreater(w[1], 0.0)
        # distance 1.2 >= bandwidth -> weight 0
        self.assertEqual(w[4], 0.0)
        # distance 0.9 gives u=0.9, w=(1-0.9^3)^3 = (1-0.729)^3 ≈ 0.0199
        self.assertAlmostEqual(w[3], 0.0199, places=3)

    def test_all_zero_when_bandwidth_is_zero(self) -> None:
        w = tricube_weights([0.0, 0.1], bandwidth=0.0)
        self.assertTrue(all(v == 0.0 for v in w))


class LowessSmoothTest(unittest.TestCase):
    def setUp(self) -> None:
        # Monotonic trend: y = 0.5*x - 0.2, with small noise
        self.xs = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        self.ys = [0.5 * x - 0.2 + 0.02 * math.sin(10 * x) for x in self.xs]

    def test_smoothed_values_have_reduced_variance(self) -> None:
        smoothed = lowess_smooth(self.xs, self.ys, fraction=0.5)
        raw_var = sum((y - sum(self.ys) / len(self.ys)) ** 2 for y in self.ys) / len(self.ys)
        smooth_var = sum((s - sum(smoothed) / len(smoothed)) ** 2 for s in smoothed) / len(smoothed)
        self.assertLessEqual(smooth_var, raw_var * 1.01)

    def test_returns_same_length(self) -> None:
        smoothed = lowess_smooth(self.xs, self.ys, fraction=0.5)
        self.assertEqual(len(smoothed), len(self.xs))

    def test_handles_uniform_x(self) -> None:
        xs = [0.5, 0.5, 0.5]
        ys = [0.1, 0.2, 0.3]
        smoothed = lowess_smooth(xs, ys, fraction=0.5)
        self.assertEqual(len(smoothed), 3)
        # With identical x, bandwidth=0, weights all zero → fallback to raw y_i
        for i, s in enumerate(smoothed):
            self.assertAlmostEqual(s, ys[i], places=4)

    def test_handles_two_points(self) -> None:
        xs = [0.0, 1.0]
        ys = [-0.3, 0.3]
        smoothed = lowess_smooth(xs, ys, fraction=0.5)
        self.assertEqual(len(smoothed), 2)


class ComputeCrossoverBoundaryTest(unittest.TestCase):
    def test_crosses_to_harmful(self) -> None:
        # Delta CER goes from negative (helps) to positive (hurts)
        points = [
            {"overlap_ratio": r, "delta_cer_separated": d}
            for r, d in [
                (0.0, -0.30),
                (0.1, -0.25),
                (0.2, -0.15),
                (0.3, -0.05),
                (0.4, 0.05),
                (0.5, 0.15),
                (0.6, 0.25),
                (0.7, 0.35),
            ]
        ]
        result = compute_crossover_boundary(points)
        self.assertEqual(result["crossover_status"], "crosses_to_harmful")
        self.assertIsNotNone(result["crossover_ratio"])
        ratio = float(result["crossover_ratio"])
        self.assertGreater(ratio, 0.25)
        self.assertLess(ratio, 0.45)

    def test_always_helpful(self) -> None:
        points = [
            {"overlap_ratio": r, "delta_cer_separated": d}
            for r, d in [(0.0, -0.3), (0.3, -0.2), (0.6, -0.1), (0.9, -0.05)]
        ]
        result = compute_crossover_boundary(points)
        self.assertEqual(result["crossover_status"], "always_helpful")
        self.assertEqual(result["crossover_ratio"], "")

    def test_always_harmful(self) -> None:
        points = [
            {"overlap_ratio": r, "delta_cer_separated": d}
            for r, d in [(0.0, 0.1), (0.3, 0.2), (0.6, 0.3), (0.9, 0.4)]
        ]
        result = compute_crossover_boundary(points)
        self.assertEqual(result["crossover_status"], "always_harmful")
        self.assertEqual(result["crossover_ratio"], "")

    def test_no_data_returns_no_crossover(self) -> None:
        result = compute_crossover_boundary([])
        self.assertEqual(result["crossover_status"], "no_crossover_detected")

    def test_single_point_returns_no_crossover(self) -> None:
        points = [{"overlap_ratio": 0.5, "delta_cer_separated": -0.1}]
        result = compute_crossover_boundary(points)
        self.assertEqual(result["crossover_status"], "no_crossover_detected")

    def test_crosses_to_helpful(self) -> None:
        # Delta CER goes from positive (hurts) to negative (helps)
        points = [
            {"overlap_ratio": r, "delta_cer_separated": d}
            for r, d in [
                (0.0, 0.3),
                (0.2, 0.1),
                (0.4, -0.1),
                (0.6, -0.3),
                (0.8, -0.5),
            ]
        ]
        result = compute_crossover_boundary(points)
        self.assertEqual(result["crossover_status"], "crosses_to_helpful")


class BootstrapCrossoverCITest(unittest.TestCase):
    def setUp(self) -> None:
        self.points = [
            {"overlap_ratio": r, "delta_cer_separated": d}
            for r, d in [
                (0.0, -0.30), (0.05, -0.28), (0.10, -0.22),
                (0.15, -0.18), (0.20, -0.12), (0.25, -0.08),
                (0.30, -0.02), (0.35, 0.04), (0.40, 0.10),
                (0.45, 0.16), (0.50, 0.22), (0.55, 0.28),
                (0.60, 0.34), (0.65, 0.38), (0.70, 0.42),
            ]
        ]

    def test_ci_bounds_are_ordered(self) -> None:
        result = bootstrap_crossover_ci(self.points, B=200, seed=42)
        ci = result["crossover_ci"]
        self.assertLessEqual(ci["lower"], ci["median"])
        self.assertLessEqual(ci["median"], ci["upper"])

    def test_bin_probabilities_in_range(self) -> None:
        result = bootstrap_crossover_ci(self.points, B=100, seed=42)
        for prob in result["bootstrap_bin_probabilities"].values():
            self.assertGreaterEqual(prob, 0.0)
            self.assertLessEqual(prob, 1.0)

    def test_crossover_found_with_high_confidence(self) -> None:
        result = bootstrap_crossover_ci(self.points, B=200, seed=42)
        self.assertGreater(float(result["crossover_ci"]["confidence"]), 0.5)

    def test_bootstrap_sample_count_is_correct(self) -> None:
        result = bootstrap_crossover_ci(self.points, B=50, seed=42)
        self.assertEqual(result["crossover_ci"]["bootstrap_samples"], 50)


class BuildBoundaryMetadataTest(unittest.TestCase):
    def setUp(self) -> None:
        self.points = [
            {"overlap_ratio": r, "delta_cer_separated": d}
            for r, d in [
                (0.0, -0.30), (0.2, -0.10), (0.4, 0.10), (0.6, 0.30), (0.8, 0.50),
            ]
        ]

    def test_contains_all_expected_keys(self) -> None:
        meta = build_boundary_metadata(self.points, B=50, seed=42)
        expected_keys = {
            "boundary_type", "crossover_ratio", "crossover_ci_lower",
            "crossover_ci_upper", "crossover_ci_median", "crossover_ci_width",
            "bootstrap_samples", "below_boundary_help_rate",
            "above_boundary_help_rate", "label",
        }
        self.assertTrue(expected_keys.issubset(meta.keys()))

    def test_label_is_frontier(self) -> None:
        meta = build_boundary_metadata(self.points, B=50, seed=42)
        self.assertEqual(meta["label"], "experimental/frontier")


class BuildDenseTrendRowsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.points = [
            {"overlap_ratio": 0.0, "delta_cer_separated": -0.3, "source_label": "test"},
            {"overlap_ratio": 0.0, "delta_cer_separated": -0.2, "source_label": "test"},
            {"overlap_ratio": 0.3, "delta_cer_separated": 0.1, "source_label": "test"},
            {"overlap_ratio": 0.3, "delta_cer_separated": 0.2, "source_label": "test"},
        ]

    def test_trend_has_ci_columns(self) -> None:
        trends = build_dense_trend_rows(self.points, B=100, seed=42)
        self.assertGreater(len(trends), 0)
        for row in trends:
            self.assertIn("bootstrap_mean_delta_cer", row)
            self.assertIn("bootstrap_se_cer", row)
            self.assertIn("bootstrap_p_helps", row)
            self.assertIn("trend_ci_lower", row)
            self.assertIn("trend_ci_upper", row)

    def test_empty_points_returns_empty_list(self) -> None:
        trends = build_dense_trend_rows([], B=100, seed=42)
        self.assertEqual(trends, [])


if __name__ == "__main__":
    unittest.main()
