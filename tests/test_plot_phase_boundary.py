"""Tests for src.plot_phase_boundary — enhanced separation phase boundary plots.

These tests verify that the plotting functions accept valid inputs, produce
output files, and do not crash.  Actual visual correctness is not asserted
programmatically (that is a visual-inspection concern).
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

# Import at module level to avoid descriptor-binding issues when accessed
# through ``self`` in test methods.
from src.plot_phase_boundary import (
    plot_bootstrap_probability_curve,
    plot_enhanced_phase_diagram,
)


class PlotPhaseBoundaryTest(unittest.TestCase):
    """Lightweight smoke tests for plot_phase_boundary functions."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="test_phase_plots_")

    # ── fixture helpers ──────────────────────────────────────────────────

    @staticmethod
    def _make_points() -> list[dict]:
        return [
            {
                "overlap_ratio": 0.10,
                "delta_cer_separated": -0.05,
                "source_label": "synthetic/silver",
                "separation_helps": True,
            },
            {
                "overlap_ratio": 0.50,
                "delta_cer_separated": 0.15,
                "source_label": "synthetic/silver",
                "separation_helps": False,
            },
            {
                "overlap_ratio": 0.85,
                "delta_cer_separated": 0.30,
                "source_label": "stable/gold",
                "separation_helps": False,
            },
        ]

    @staticmethod
    def _make_trend_rows() -> list[dict]:
        return [
            {"overlap_bin": 0.10, "mean_delta_cer_separated": -0.05, "sample_count": 1},
            {"overlap_bin": 0.50, "mean_delta_cer_separated": 0.15, "sample_count": 1},
            {"overlap_bin": 0.85, "mean_delta_cer_separated": 0.30, "sample_count": 1},
        ]

    @staticmethod
    def _make_boundary_metadata() -> dict:
        return {
            "boundary_type": "crosses_to_harmful",
            "crossover_ratio": 0.25,
            "crossover_ci_lower": 0.18,
            "crossover_ci_upper": 0.32,
            "crossover_ci_width": 0.14,
            "bootstrap_samples": 500,
            "below_boundary_help_rate": 0.8,
            "above_boundary_help_rate": 0.1,
            "label": "experimental/frontier",
        }

    @staticmethod
    def _make_dense_trend() -> list[dict]:
        return [
            {
                "overlap_bin": 0.10,
                "sample_count": 2,
                "bootstrap_mean_delta_cer": -0.05,
                "bootstrap_se_cer": 0.01,
                "bootstrap_p_helps": 0.9,
                "trend_ci_lower": -0.07,
                "trend_ci_upper": -0.03,
            },
            {
                "overlap_bin": 0.50,
                "sample_count": 3,
                "bootstrap_mean_delta_cer": 0.15,
                "bootstrap_se_cer": 0.02,
                "bootstrap_p_helps": 0.1,
                "trend_ci_lower": 0.11,
                "trend_ci_upper": 0.19,
            },
        ]

    # ── tests ────────────────────────────────────────────────────────────

    def test_enhanced_phase_diagram_no_boundary(self) -> None:
        """Should produce a PNG even without boundary metadata."""
        out = Path(self.tmpdir) / "diagram.png"
        plot_enhanced_phase_diagram(
            self._make_points(),
            self._make_trend_rows(),
            boundary_metadata=None,
            out_path=str(out),
        )
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 500, "PNG too small — plot may be empty")

    def test_enhanced_phase_diagram_with_boundary(self) -> None:
        """Should include crossover + CI markers without crashing."""
        out = Path(self.tmpdir) / "diagram_boundary.png"
        plot_enhanced_phase_diagram(
            self._make_points(),
            self._make_trend_rows(),
            boundary_metadata=self._make_boundary_metadata(),
            out_path=str(out),
        )
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 500)

    def test_bootstrap_probability_curve_empty_dense_trend(self) -> None:
        """Should handle empty dense_trend gracefully."""
        out = Path(self.tmpdir) / "prob_empty.png"
        plot_bootstrap_probability_curve(
            [],
            boundary_metadata=None,
            out_path=str(out),
        )
        self.assertTrue(out.exists())

    def test_bootstrap_probability_curve_with_data(self) -> None:
        """Should render probability curve with CI bands."""
        out = Path(self.tmpdir) / "prob.png"
        plot_bootstrap_probability_curve(
            self._make_dense_trend(),
            boundary_metadata=self._make_boundary_metadata(),
            out_path=str(out),
        )
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 500)

    def test_plot_functions_are_callable(self) -> None:
        """Sanity-check that the imported callables are functions."""
        self.assertTrue(callable(plot_enhanced_phase_diagram))
        self.assertTrue(callable(plot_bootstrap_probability_curve))


if __name__ == "__main__":
    unittest.main()
