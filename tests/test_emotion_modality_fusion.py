"""Unit tests for tri-modal emotion fusion (issue #835).

The fusion/CV logic is tested on deterministic synthetic data (numpy rng seeded) so the H1/H2/H3
verdicts are checked without any ollama/Whisper/librosa. Must pass under `unittest discover`.
"""
from __future__ import annotations

import math
import unittest

import numpy as np

from src import emotion_modality_fusion as emf


def _linear_dataset(n=80, weights=(2.0, 3.0, 1.5), noise=0.05, seed=0):
    """y depends on all three single-column groups a,b,c (so every modality contributes)."""
    rng = np.random.default_rng(seed)
    a = rng.normal(size=n)
    b = rng.normal(size=n)
    c = rng.normal(size=n)
    y = weights[0] * a + weights[1] * b + weights[2] * c + noise * rng.normal(size=n)
    X = np.column_stack([a, b, c])
    groups = {"a": [0], "b": [1], "c": [2]}
    return X, y, groups


class TestFitEvalCV(unittest.TestCase):
    def test_fusion_beats_best_single(self):
        X, y, groups = _linear_dataset()
        out = emf.fit_eval_cv(X, y, groups, n_splits=5, seed=0)
        per = out["per_group"]
        best_single = max(per[g]["r2_cv"] for g in groups)  # only single-modality groups
        self.assertGreater(out["fused_r2"], best_single)         # H1: fusion adds
        self.assertTrue(out["H1_fused_beats_best_single"])
        self.assertGreater(out["fused_r2"], 0.7)                 # signal genuinely recovered

    def test_ablation_detects_each_contribution(self):
        X, y, groups = _linear_dataset()
        out = emf.fit_eval_cv(X, y, groups, n_splits=5, seed=0)
        # leaving out any group (all contribute) should drop fused R²
        for g in groups:
            self.assertGreater(out["ablations"][g]["drop_vs_fused"], 0.0)
        self.assertTrue(out["H2_each_modality_contributes"])

    def test_null_target_no_fusion_win(self):
        rng = np.random.default_rng(1)
        X = rng.normal(size=(60, 3))
        y = rng.normal(size=60)  # pure noise, unrelated to X
        groups = {"a": [0], "b": [1], "c": [2]}
        out = emf.fit_eval_cv(X, y, groups, n_splits=5, seed=0)
        self.assertLess(out["fused_r2"], 0.3)         # nothing to predict
        self.assertFalse(out["H2_each_modality_contributes"])  # no group adds real signal

    def test_spearman_reported(self):
        X, y, groups = _linear_dataset()
        out = emf.fit_eval_cv(X, y, groups, n_splits=5, seed=0)
        self.assertIn("fused_spearman", out)
        self.assertGreater(out["fused_spearman"], 0.7)
        self.assertIn("H3_fused_ranking_ok", out)

    def test_permutation_importance_present(self):
        X, y, groups = _linear_dataset()
        out = emf.fit_eval_cv(X, y, groups, n_splits=5, seed=0)
        imp = out["permutation_importance"]
        self.assertEqual(len(imp), 3)
        # feature b has the largest weight (3.0) -> highest importance
        self.assertEqual(max(imp, key=lambda k: imp[k]), 1)

    def test_binary_auc_reported(self):
        X, y, groups = _linear_dataset()
        out = emf.fit_eval_cv(X, y, groups, n_splits=5, seed=0)
        self.assertIn("fused_auc", out)
        self.assertGreater(out["fused_auc"], 0.7)

    def test_nan_safe_constant_target(self):
        X = np.random.default_rng(2).normal(size=(20, 3))
        y = np.ones(20)  # constant -> R² undefined
        groups = {"a": [0], "b": [1], "c": [2]}
        out = emf.fit_eval_cv(X, y, groups, n_splits=5, seed=0)
        self.assertTrue(math.isnan(out["fused_r2"]) or out["fused_r2"] <= 0.0)
        # must not crash and must produce verdict keys
        self.assertIn("H1_fused_beats_best_single", out)
        self.assertIn("H2_each_modality_contributes", out)

    def test_too_few_rows_safe(self):
        X = np.random.default_rng(3).normal(size=(4, 3))
        y = np.arange(4, dtype=float)
        groups = {"a": [0], "b": [1], "c": [2]}
        out = emf.fit_eval_cv(X, y, groups, n_splits=5, seed=0)  # n<n_splits handled
        self.assertIn("fused_r2", out)


class TestFeatureRowToVector(unittest.TestCase):
    def test_row_to_vector_order(self):
        row = {
            "llm_valence": -0.5, "llm_arousal": 0.4,
            "lexical_valence": 0.1, "lexical_arousal": 0.2,
            "acoustic_arousal": 1.3,
        }
        vec = emf.feature_vector(row)
        self.assertEqual(list(vec), [-0.5, 0.4, 0.1, 0.2, 1.3])

    def test_groups_cover_all_features(self):
        # the declared FEATURE_GROUPS column indices must exactly partition the feature vector
        idxs = sorted(i for g in emf.FEATURE_GROUPS.values() for i in g)
        self.assertEqual(idxs, list(range(len(emf.FEATURE_NAMES))))


class TestRunOrchestration(unittest.TestCase):
    """End-to-end run() with injected rows (no ollama/Whisper/librosa). Covers the two-target wiring
    and the CSV/JSON/FINDINGS writers."""

    def _rows(self):
        rng = np.random.default_rng(0)
        rows = []
        for i in range(24):
            a = rng.normal()      # acoustic feature drives the acoustic target
            v = rng.normal()      # llm valence drives the semantic target
            rows.append({
                "sample_id": f"s{i}", "tier": "T", "overlap_ratio": 0.3, "speaker": 1, "speaker_label": "con",
                "llm_valence": v, "llm_arousal": rng.normal() * 0.1,
                "lexical_valence": rng.normal() * 0.1, "lexical_arousal": rng.normal() * 0.1,
                "acoustic_arousal": a,
                "target_emotion_distortion": 2.0 * a + 0.05 * rng.normal(),
                "target_semantic_distortion": 2.0 * v + 0.05 * rng.normal(),
            })
        return rows

    def test_run_writes_two_target_summary(self):
        import json
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as td:
            out = emf.run(rows=self._rows(), out_dir=td, seed=0)
            out = emf.Path(out)
            for name in ("fusion_curve.csv", "summary.json", "FINDINGS.md"):
                self.assertTrue((out / name).exists(), f"missing {name}")
            s = json.loads((out / "summary.json").read_text())
            self.assertEqual(set(s["by_target"]), {"acoustic_emotion_damage", "semantic_emotion_damage"})
            # own-modality should win each target
            self.assertEqual(s["best_single_per_target"]["acoustic_emotion_damage"], "acoustic")
            self.assertEqual(s["best_single_per_target"]["semantic_emotion_damage"], "llm")
            self.assertIn("fusion_ever_beats_best_single", s)
            self.assertIn("Conclusion", (out / "FINDINGS.md").read_text())


if __name__ == "__main__":
    unittest.main()
