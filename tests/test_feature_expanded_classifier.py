"""Tests for RQ32 feature-expanded classifier (experimental/frontier).

Pin the PURE helpers (Shannon entropy, char ratio, runtime ratio, metadata
extraction, feature-matrix assembly) and include a RandomForest smoke test
(train on tiny data, predict, check output shape). No Whisper / no ASR run.

The analysis module lives under results/frontier/ rather than src/, so it is
loaded with importlib.util.spec_from_file_location (same pattern as the
harness contract_rules test). Issue #939.
"""
from __future__ import annotations

import importlib.util
import math
import sys
import unittest
from pathlib import Path

import numpy as np

# Inject project root onto sys.path so any src/ imports inside the analysis
# module (if added later) resolve; matches the repo's standard test setup.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Load results/frontier/feature_expanded_classifier/feature_expanded_classifier_analysis.py
# without requiring it to live on sys.path as a package.
_ANALYSIS_PATH = (
    _PROJECT_ROOT
    / "results"
    / "frontier"
    / "feature_expanded_classifier"
    / "feature_expanded_classifier_analysis.py"
)
_spec = importlib.util.spec_from_file_location(
    "feature_expanded_classifier_analysis", _ANALYSIS_PATH
)
assert _spec is not None and _spec.loader is not None
fec = importlib.util.module_from_spec(_spec)
sys.modules["feature_expanded_classifier_analysis"] = fec
_spec.loader.exec_module(fec)


class TestShannonEntropyNats(unittest.TestCase):
    def test_empty_returns_zero(self) -> None:
        self.assertEqual(fec.shannon_entropy_nats([]), 0.0)

    def test_single_nonzero_returns_zero(self) -> None:
        # entropy undefined for a point mass -> 0.0
        self.assertEqual(fec.shannon_entropy_nats([42]), 0.0)
        self.assertEqual(fec.shannon_entropy_nats([0, 42]), 0.0)

    def test_monoscript_balanced_two_speakers(self) -> None:
        # equal split of two non-zero lengths -> ln(2) nats
        h = fec.shannon_entropy_nats([10, 10])
        self.assertAlmostEqual(h, math.log(2.0), places=6)

    def test_multilingual_balanced_three_speakers(self) -> None:
        # equal split of three -> ln(3) nats
        h = fec.shannon_entropy_nats([5, 5, 5])
        self.assertAlmostEqual(h, math.log(3.0), places=6)

    def test_zero_length_entries_excluded(self) -> None:
        # inactive speakers (length 0) carry no distributional information
        self.assertAlmostEqual(
            fec.shannon_entropy_nats([10, 10, 0, 0]),
            math.log(2.0),
            places=6,
        )

    def test_extremal_distribution_low_entropy(self) -> None:
        # heavily skewed distribution -> entropy close to 0
        h = fec.shannon_entropy_nats([1000, 1])
        self.assertLess(h, 0.05)


class TestCharRatioSafe(unittest.TestCase):
    def test_zero_division_returns_zero(self) -> None:
        self.assertEqual(fec.char_ratio_safe(10, 0), 0.0)
        self.assertEqual(fec.char_ratio_safe(0, 0), 0.0)

    def test_negative_denominator_returns_zero(self) -> None:
        # defensive: negative mix chars treated as undefined
        self.assertEqual(fec.char_ratio_safe(10, -5), 0.0)

    def test_normal_ratio(self) -> None:
        self.assertAlmostEqual(fec.char_ratio_safe(20, 10), 2.0, places=6)
        self.assertAlmostEqual(fec.char_ratio_safe(5, 10), 0.5, places=6)

    def test_returns_float(self) -> None:
        self.assertIsInstance(fec.char_ratio_safe(3, 7), float)


class TestRuntimeRatioSafe(unittest.TestCase):
    def test_zero_division_returns_zero(self) -> None:
        self.assertEqual(fec.runtime_ratio_safe(10.0, 0.0), 0.0)
        self.assertEqual(fec.runtime_ratio_safe(0.0, 0.0), 0.0)

    def test_negative_denominator_returns_zero(self) -> None:
        self.assertEqual(fec.runtime_ratio_safe(10.0, -2.0), 0.0)

    def test_normal_ratio(self) -> None:
        self.assertAlmostEqual(fec.runtime_ratio_safe(6.0, 3.0), 2.0, places=6)
        self.assertAlmostEqual(fec.runtime_ratio_safe(3.0, 6.0), 0.5, places=6)


class TestExtractMetadataFeatures(unittest.TestCase):
    def test_returns_all_seven_metadata_keys(self) -> None:
        window = {
            "separated_runtime_sec": 10.0,
            "mixed_runtime_sec": 5.0,
            "separated_total_length": 100,
            "mixed_text_length": 50,
            "separated_text_per_speaker": {"s1": "aaaa", "s2": "bbbb"},
        }
        meta = fec.extract_metadata_features(window)
        self.assertEqual(set(meta.keys()), set(fec.METADATA_FEATURES))
        self.assertEqual(len(meta), 7)

    def test_correct_values_for_balanced_window(self) -> None:
        window = {
            "separated_runtime_sec": 10.0,
            "mixed_runtime_sec": 5.0,
            "separated_total_length": 100,
            "mixed_text_length": 50,
            "separated_text_per_speaker": {"s1": "aaaa", "s2": "bbbb"},
        }
        meta = fec.extract_metadata_features(window)
        self.assertAlmostEqual(meta["runtime_ratio"], 2.0, places=6)
        self.assertAlmostEqual(meta["sep_total_chars"], 100.0, places=6)
        self.assertAlmostEqual(meta["mix_total_chars"], 50.0, places=6)
        self.assertAlmostEqual(meta["char_ratio"], 2.0, places=6)
        self.assertAlmostEqual(meta["num_active_speakers_sep"], 2.0, places=6)
        self.assertAlmostEqual(meta["avg_speaker_length_sep"], 4.0, places=6)
        # equal split of two -> ln(2)
        self.assertAlmostEqual(
            meta["length_entropy_speakers"], math.log(2.0), places=6
        )

    def test_missing_fields_default_to_zero(self) -> None:
        # empty window -> all zeros, no exception
        meta = fec.extract_metadata_features({})
        for k in fec.METADATA_FEATURES:
            self.assertEqual(meta[k], 0.0, f"{k} should be 0.0 for empty window")

    def test_none_values_handled(self) -> None:
        # None values should be coerced to 0 via `or 0.0` guard
        meta = fec.extract_metadata_features({
            "separated_runtime_sec": None,
            "mixed_runtime_sec": None,
            "separated_total_length": None,
            "mixed_text_length": None,
            "separated_text_per_speaker": None,
        })
        self.assertEqual(meta["runtime_ratio"], 0.0)
        self.assertEqual(meta["num_active_speakers_sep"], 0.0)
        self.assertEqual(meta["avg_speaker_length_sep"], 0.0)
        self.assertEqual(meta["length_entropy_speakers"], 0.0)

    def test_empty_speaker_segments_excluded_from_active_count(self) -> None:
        window = {
            "separated_runtime_sec": 1.0,
            "mixed_runtime_sec": 1.0,
            "separated_total_length": 5,
            "mixed_text_length": 5,
            "separated_text_per_speaker": {"s1": "aaa", "s2": "", "s3": "bb"},
        }
        meta = fec.extract_metadata_features(window)
        self.assertEqual(meta["num_active_speakers_sep"], 2.0)
        self.assertAlmostEqual(meta["avg_speaker_length_sep"], 2.5, places=6)


class TestBuildFeatureMatrix(unittest.TestCase):
    def _make_tracks(self) -> list[dict]:
        return [
            {
                "dataset": "gold",
                "track_id": "gold_track_1",
                "true_mode": "Non-hallucinated",
                "rq23_predicted_mode": "Non-hallucinated",
                "cr": 0.8,
                "lang_id_entropy": 0.0,
                "length_ratio": 0.5,
                "content_similarity": 0.1,
                "num_speakers": 2.0,
            },
            {
                "dataset": "aishell4",
                "track_id": "0",
                "true_mode": "Mode_S",
                "rq23_predicted_mode": "Mode_S",
                "cr": 1.5,
                "lang_id_entropy": 0.5,
                "length_ratio": 1.2,
                "content_similarity": 0.3,
                "num_speakers": 3.0,
            },
        ]

    def _make_a4_windows(self) -> dict:
        return {
            0: {
                "separated_runtime_sec": 10.0,
                "mixed_runtime_sec": 5.0,
                "separated_total_length": 100,
                "mixed_text_length": 50,
                "separated_text_per_speaker": {"s1": "aaaa", "s2": "bbbb"},
            }
        }

    def test_matrix_shape_is_n_tracks_x_13_features(self) -> None:
        X, y, enriched = fec.build_feature_matrix(self._make_tracks(), self._make_a4_windows())
        self.assertEqual(X.shape, (2, 13))
        self.assertEqual(y.shape, (2,))
        self.assertEqual(len(enriched), 2)

    def test_no_nan_or_inf_in_matrix(self) -> None:
        X, _, _ = fec.build_feature_matrix(self._make_tracks(), self._make_a4_windows())
        self.assertFalse(np.any(np.isnan(X)))
        self.assertFalse(np.any(np.isinf(X)))

    def test_gold_track_has_metadata_zeroed(self) -> None:
        X, _, enriched = fec.build_feature_matrix(self._make_tracks(), self._make_a4_windows())
        # gold track is index 0; metadata features are indices 5..11, indicator is 12
        for i in range(5, 12):
            self.assertEqual(X[0, i], 0.0, f"gold metadata feature idx {i} should be 0")
        self.assertEqual(X[0, 12], 0.0)  # has_metadata indicator

    def test_aishell4_track_has_metadata_indicator_one(self) -> None:
        X, _, enriched = fec.build_feature_matrix(self._make_tracks(), self._make_a4_windows())
        # aishell4 track is index 1; indicator should be 1.0
        self.assertEqual(X[1, 12], 1.0)
        # and runtime_ratio (idx 5) should be 2.0
        self.assertAlmostEqual(X[1, 5], 2.0, places=6)

    def test_aishell4_without_matching_window_zeroed(self) -> None:
        # track_id not in a4_windows -> metadata zeroed, indicator 0
        tracks = self._make_tracks()
        tracks[1]["track_id"] = "999"  # not in windows dict
        X, _, enriched = fec.build_feature_matrix(tracks, self._make_a4_windows())
        self.assertEqual(X[1, 12], 0.0)  # has_metadata indicator
        for i in range(5, 12):
            self.assertEqual(X[1, i], 0.0)

    def test_labels_match_mode_to_idx(self) -> None:
        X, y, _ = fec.build_feature_matrix(self._make_tracks(), self._make_a4_windows())
        self.assertEqual(y[0], fec.MODE_TO_IDX["Non-hallucinated"])
        self.assertEqual(y[1], fec.MODE_TO_IDX["Mode_S"])

    def test_enriched_tracks_carry_metadata_fields(self) -> None:
        X, _, enriched = fec.build_feature_matrix(self._make_tracks(), self._make_a4_windows())
        for k in fec.METADATA_FEATURES:
            self.assertIn(k, enriched[1])
        self.assertIn(fec.INDICATOR_FEATURE, enriched[1])

    def test_feature_count_constant(self) -> None:
        # 5 original + 7 metadata + 1 indicator = 13
        self.assertEqual(len(fec.ALL_FEATURES), 13)
        self.assertEqual(
            len(fec.ORIGINAL_FEATURES) + len(fec.METADATA_FEATURES) + 1,
            len(fec.ALL_FEATURES),
        )


class TestRandomForestSmoke(unittest.TestCase):
    """Smoke test: train a small RF on synthetic separable data, predict, and
    check the output shape and basic separability. Does NOT exercise the full
    LOO-CV (that is the analysis script's job, not the unit-test gate)."""

    def test_train_predict_shapes_and_separability(self) -> None:
        rng = np.random.default_rng(123)
        n_per_class = 20
        n_classes = 2
        # two well-separated Gaussian blobs in 4D
        X0 = rng.normal(loc=0.0, scale=0.3, size=(n_per_class, 4))
        X1 = rng.normal(loc=3.0, scale=0.3, size=(n_per_class, 4))
        X = np.vstack([X0, X1])
        y = np.array([0] * n_per_class + [1] * n_per_class, dtype=int)

        rf = fec.RandomForest(
            n_trees=10, max_depth=4, min_samples_split=2,
            class_weight="sqrt", seed=42,
        )
        rf.fit(X, y, n_classes)
        preds = rf.predict(X)

        self.assertEqual(preds.shape, (len(y),))
        # on training data with well-separated blobs, RF should fit near-perfectly
        acc = float((preds == y).mean())
        self.assertGreaterEqual(acc, 0.95)

    def test_predict_returns_int_array(self) -> None:
        rng = np.random.default_rng(7)
        X = rng.normal(size=(15, 3))
        y = np.array([0, 1] * 7 + [0], dtype=int)
        rf = fec.RandomForest(
            n_trees=5, max_depth=3, class_weight="sqrt", seed=1,
        )
        rf.fit(X, y, 2)
        preds = rf.predict(X)
        self.assertEqual(preds.shape, (15,))
        self.assertEqual(preds.dtype, int)

    def test_feature_importances_normalised(self) -> None:
        rng = np.random.default_rng(11)
        X = rng.normal(size=(30, 4))
        y = (X[:, 0] > 0).astype(int)
        rf = fec.RandomForest(
            n_trees=8, max_depth=4, class_weight="sqrt", seed=2,
        )
        rf.fit(X, y, 2)
        fi = rf.feature_importances_
        self.assertIsNotNone(fi)
        self.assertEqual(fi.shape, (4,))
        # importances sum to 1 (or 0 if no splits, but here feature 0 is informative)
        self.assertAlmostEqual(float(fi.sum()), 1.0, places=5)
        # the informative feature should dominate
        self.assertGreater(float(fi[0]), float(fi[1]))

    def test_constant_labels_produce_no_crash(self) -> None:
        # edge case: all same label -> tree becomes a leaf, predict should still work
        X = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])
        y = np.array([1, 1, 1], dtype=int)
        rf = fec.RandomForest(
            n_trees=3, max_depth=2, class_weight="sqrt", seed=3,
        )
        rf.fit(X, y, 2)
        preds = rf.predict(X)
        self.assertTrue(np.all(preds == 1))


if __name__ == "__main__":
    unittest.main()
