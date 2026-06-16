"""Tests for src.learned_router — supervised routing module."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

try:
    import sklearn  # noqa: F401
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False


# ---------------------------------------------------------------------------
# Helpers to create minimal CSV fixtures
# ---------------------------------------------------------------------------
METHODS = ["mixed_whisper", "separated_whisper", "separated_whisper_cleaned"]


def _make_cer_csv(tmp: Path, rows: list[dict]) -> Path:
    path = tmp / "cer.csv"
    fieldnames = ["sample_id", "tier", "split", "overlap_level", "method",
                   "ref_path", "hyp_path", "ref_chars", "hyp_chars",
                   "edit_distance", "cer"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def _make_routing_csv(tmp: Path, rows: list[dict]) -> Path:
    path = tmp / "routing.csv"
    fieldnames = [
        "sample_id", "tier", "split", "strategy", "selected_method",
        "decision_rule",
        "mixed_segments_count", "separated_segments_count",
        "cleaned_segments_count",
        "mixed_text_length", "separated_text_length", "cleaned_text_length",
        "text_length_ratio", "mixed_runtime_sec", "separated_runtime_sec",
        "cleaned_runtime_sec", "runtime_ratio",
        "duplicate_removed_count",
        "notes",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def _sample_cer_row(sid, tier, split, overlap, method, cer):
    return {
        "sample_id": sid, "tier": tier, "split": split,
        "overlap_level": str(overlap), "method": method,
        "ref_path": "", "hyp_path": "",
        "ref_chars": "100", "hyp_chars": "100",
        "edit_distance": str(int(cer * 100)), "cer": str(cer),
    }


def _sample_routing_row(sid, tier, split):
    return {
        "sample_id": sid, "tier": tier, "split": split,
        "strategy": "v2_full_features", "selected_method": "mixed_whisper",
        "decision_rule": "test",
        "mixed_segments_count": "2", "separated_segments_count": "4",
        "cleaned_segments_count": "3",
        "mixed_text_length": "50", "separated_text_length": "120",
        "cleaned_text_length": "80",
        "text_length_ratio": "2.4",
        "mixed_runtime_sec": "1.0", "separated_runtime_sec": "2.0",
        "cleaned_runtime_sec": "2.0",
        "runtime_ratio": "2.0",
        "duplicate_removed_count": "5",
        "notes": "",
    }


# ---------------------------------------------------------------------------
# Base class with shared fixture logic
# ---------------------------------------------------------------------------
class _CSVFixtureMixin:
    """Create minimal dev+test CER and routing CSVs (10 dev + 10 test)."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        tmp = Path(self._tmpdir.name)
        cer_rows: list[dict] = []
        routing_rows: list[dict] = []
        tiers = [
            ("SyntheticNoOverlap", 0),
            ("SyntheticLightOverlap", 1),
        ]
        for split_name, idx_range in [("dev", range(1, 6)), ("test", range(1, 6))]:
            for tier_name, overlap in tiers:
                for i in idx_range:
                    sid = f"{tier_name}_{split_name}_{i:02d}"
                    if overlap == 0:
                        cer_rows.append(_sample_cer_row(sid, tier_name, split_name, overlap, "mixed_whisper", 0.05))
                        cer_rows.append(_sample_cer_row(sid, tier_name, split_name, overlap, "separated_whisper", 0.30))
                        cer_rows.append(_sample_cer_row(sid, tier_name, split_name, overlap, "separated_whisper_cleaned", 0.25))
                    else:
                        cer_rows.append(_sample_cer_row(sid, tier_name, split_name, overlap, "mixed_whisper", 0.40))
                        cer_rows.append(_sample_cer_row(sid, tier_name, split_name, overlap, "separated_whisper", 0.10))
                        cer_rows.append(_sample_cer_row(sid, tier_name, split_name, overlap, "separated_whisper_cleaned", 0.08))
                    routing_rows.append(_sample_routing_row(sid, tier_name, split_name))

        self.cer_csv = _make_cer_csv(tmp, cer_rows)
        self.routing_csv = _make_routing_csv(tmp, routing_rows)

    def tearDown(self):
        self._tmpdir.cleanup()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestOracleLabels(_CSVFixtureMixin, unittest.TestCase):
    def test_load_oracle_picks_min_cer(self):
        from src.learned_router import load_oracle_labels
        oracle = load_oracle_labels(self.cer_csv)
        self.assertEqual(oracle["SyntheticNoOverlap_dev_01"], "mixed_whisper")
        self.assertEqual(oracle["SyntheticLightOverlap_dev_01"], "separated_whisper_cleaned")

    def test_oracle_returns_all_samples(self):
        from src.learned_router import load_oracle_labels
        oracle = load_oracle_labels(self.cer_csv)
        self.assertEqual(len(oracle), 20)


class TestLoadFeatures(_CSVFixtureMixin, unittest.TestCase):
    def test_load_features_returns_correct_keys(self):
        from src.learned_router import load_features, FEATURE_NAMES
        features = load_features(self.routing_csv)
        self.assertEqual(len(features), 20)
        for sid, feat in features.items():
            for fn in FEATURE_NAMES:
                self.assertIn(fn, feat, f"Missing feature {fn} for {sid}")

    def test_feature_values_parsed(self):
        from src.learned_router import load_features
        features = load_features(self.routing_csv)
        f = features["SyntheticNoOverlap_dev_01"]
        self.assertAlmostEqual(f["text_length_ratio"], 2.4, places=5)
        self.assertEqual(f["duplicate_removed_count"], 5.0)


class TestRouterDataset(_CSVFixtureMixin, unittest.TestCase):
    def test_from_csvs_shape(self):
        from src.learned_router import RouterDataset
        ds = RouterDataset.from_csvs(self.cer_csv, self.routing_csv)
        self.assertEqual(ds.X.shape, (20, 10))
        self.assertEqual(ds.y.shape, (20,))

    def test_train_test_split(self):
        from src.learned_router import RouterDataset
        ds = RouterDataset.from_csvs(self.cer_csv, self.routing_csv)
        train, test = ds.train_test_split()
        self.assertEqual(len(train.sample_ids), 10)
        self.assertEqual(len(test.sample_ids), 10)


@unittest.skipUnless(_HAS_SKLEARN, "scikit-learn not installed")
class TestTrainRouter(_CSVFixtureMixin, unittest.TestCase):
    def _run_model(self, model_type):
        from src.learned_router import RouterDataset, train_router
        ds = RouterDataset.from_csvs(self.cer_csv, self.routing_csv)
        return train_router(ds, model_type=model_type)

    def test_train_returns_result_logistic_regression(self):
        result = self._run_model("logistic_regression")
        self.assertGreaterEqual(result.train_accuracy, 0.0)
        self.assertLessEqual(result.train_accuracy, 1.0)
        self.assertGreaterEqual(result.test_accuracy, 0.0)
        self.assertLessEqual(result.test_accuracy, 1.0)
        self.assertEqual(len(result.predictions), 10)

    def test_train_returns_result_decision_tree(self):
        result = self._run_model("decision_tree")
        self.assertGreaterEqual(result.train_accuracy, 0.0)
        self.assertLessEqual(result.train_accuracy, 1.0)
        self.assertGreaterEqual(result.test_accuracy, 0.0)
        self.assertLessEqual(result.test_accuracy, 1.0)
        self.assertEqual(len(result.predictions), 10)

    def test_decision_tree_has_text(self):
        result = self._run_model("decision_tree")
        self.assertGreater(len(result.tree_text), 0)
        self.assertTrue(
            "overlap_level" in result.tree_text or "text_length_ratio" in result.tree_text
        )

    def test_summary_dict(self):
        result = self._run_model("logistic_regression")
        summary = result.to_summary_dict()
        self.assertIn("model_name", summary)
        self.assertIn("train_accuracy", summary)
        self.assertIn("test_accuracy", summary)


@unittest.skipUnless(_HAS_SKLEARN, "scikit-learn not installed")
class TestCERComparison(_CSVFixtureMixin, unittest.TestCase):
    def test_comparison_structure(self):
        from src.learned_router import (
            RouterDataset, train_router, compute_cer_comparison,
        )
        ds = RouterDataset.from_csvs(self.cer_csv, self.routing_csv)
        result = train_router(ds, model_type="decision_tree")
        comp = compute_cer_comparison(self.cer_csv, result.predictions, split="test")
        self.assertEqual(comp["split"], "test")
        self.assertEqual(comp["n_samples"], 10)
        self.assertIn("learned_router", comp["average_cer"])
        self.assertIn("oracle_best", comp["average_cer"])
        # Learned router CER should be >= oracle (can't beat oracle)
        self.assertGreaterEqual(
            comp["average_cer"]["learned_router"],
            comp["average_cer"]["oracle_best"] - 1e-6,
        )


if __name__ == "__main__":
    unittest.main()
