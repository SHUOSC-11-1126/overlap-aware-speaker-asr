"""RQ32: Feature expansion for Diverse<->Non-hallucinated classification.

RQ28 (PR #933) proved that the Diverse<->Non-hallucinated confusion is
FUNDAMENTAL -- a numpy-only random forest on RQ23's 5 transcript features (cr,
lang_id_entropy, length_ratio, content_similarity, num_speakers) produced the
SAME 17 Diverse<->Non-hallucinated off-diagonal errors as RQ23's linear
classifier. The confusion is not a model-capacity issue (linear vs non-linear
gained 0 reduction on the load-bearing boundary) but a feature-overlap issue.

This study tests whether EXPANDING the feature set with 7 runtime/transcript
metadata features extracted from the AISHELL-4 validation windows can break the
confusion. The 7 new features are:

- runtime_ratio -- separated ASR runtime / mixed ASR runtime
- sep_total_chars -- total character count of the separated transcript
- mix_total_chars -- character count of the mixed transcript
- char_ratio -- sep_total_chars / mix_total_chars (0 when mix is empty)
- num_active_speakers_sep -- number of non-empty speaker segments
- avg_speaker_length_sep -- mean characters per non-empty speaker segment
- length_entropy_speakers -- Shannon entropy (nats) of per-speaker length dist

For the 600 gold tracks (where metadata is not available) the 7 metadata
features are set to 0.0 and a `has_metadata` binary indicator (0 for gold, 1
for AISHELL-4) is added. This gives a 13-feature matrix
(5 original + 7 metadata + 1 indicator) over the same 677 tracks.

The same numpy-only random forest (100 trees, max_depth=10, sqrt
inverse-frequency class weighting, weighted Gini impurity, bootstrap
aggregation, LOO-CV) from RQ28 is retrained on the expanded matrix.

Hypotheses (pre-registered)
----------------------------
- H32a: Expanded-feature RF LOO accuracy > 96.9% (RQ28's 5-feature RF).
  Kill: accuracy <= 96.9%.
- H32b: AISHELL-4 mode-routed sensitivity > 90%. Kill: sensitivity <= 90%.
  Sensitivity = (truly hallucinated AND predicted hallucinated) /
                (truly hallucinated), where "predicted hallucinated" =
                predicted_mode in {Mode_R, Mode_S, Diverse}.
- H32c: Diverse<->Non-hallucinated off-diagonal < 17 (RQ28's count).
  Kill: off-diagonal >= 17.

Label: experimental/frontier. Closes #939.
"""
from __future__ import annotations

import csv
import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np

# --------------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
RQ23_CSV = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "per_track_mode_classifier"
    / "mode_classifier_results.csv"
)
RQ23_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "per_track_mode_classifier"
    / "mode_classifier_results.json"
)
A4_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "feature_expanded_classifier"
OUT_CSV = OUT_DIR / "feature_expanded_classifier_results.csv"
OUT_JSON = OUT_DIR / "feature_expanded_classifier_results.json"

# --------------------------------------------------------------- constants
MODES = ["Mode_R", "Mode_S", "Diverse", "Non-hallucinated"]
MODE_TO_IDX = {m: i for i, m in enumerate(MODES)}

ORIGINAL_FEATURES = [
    "cr",
    "lang_id_entropy",
    "length_ratio",
    "content_similarity",
    "num_speakers",
]
METADATA_FEATURES = [
    "runtime_ratio",
    "sep_total_chars",
    "mix_total_chars",
    "char_ratio",
    "num_active_speakers_sep",
    "avg_speaker_length_sep",
    "length_entropy_speakers",
]
INDICATOR_FEATURE = "has_metadata"
ALL_FEATURES = ORIGINAL_FEATURES + METADATA_FEATURES + [INDICATOR_FEATURE]  # 13 features

SEED = 42
N_TREES = 100
MAX_DEPTH = 10
MIN_SAMPLES_SPLIT = 5
CLASS_WEIGHT = "sqrt"  # matches RQ23/RQ28 sqrt inverse-frequency protocol

# RQ23 / RQ28 baseline numbers (for comparison)
RQ23_LOO_ACCURACY = 0.957164
RQ23_OFF_DIAGONAL = 29
RQ23_DIVERSE_NONHALLUC_OFFDIAG = 17
RQ23_A4_SENSITIVITY = 0.837838

RQ28_LOO_ACCURACY = 0.968981
RQ28_OFF_DIAGONAL = 21
RQ28_DIVERSE_NONHALLUC_OFFDIAG = 17
RQ28_A4_SENSITIVITY = 0.864865

EPS = 1e-9


# --------------------------------------------------------------- metadata feature extraction
def shannon_entropy_nats(lengths: list[int]) -> float:
    """Shannon entropy (base e, nats) of a non-negative length distribution.

    The lengths are normalised to a probability distribution. Zero-length
    entries are excluded (they represent inactive speakers and carry no
    distributional information). Returns 0.0 if fewer than 2 non-zero lengths
    (entropy is undefined for a point mass).
    """
    positive = [x for x in lengths if x > 0]
    n = len(positive)
    if n < 2:
        return 0.0
    total = float(sum(positive))
    if total <= 0:
        return 0.0
    h = 0.0
    for x in positive:
        p = x / total
        if p > 0:
            h -= p * math.log(p)
    return h


def char_ratio_safe(sep_chars: int, mix_chars: int) -> float:
    """sep_total_chars / mix_total_chars with safe zero-denominator handling.

    Returns 0.0 when mix_chars == 0 (ratio undefined). The RF can disambiguate
    this case via the separate `sep_total_chars` and `mix_total_chars` features.
    """
    if mix_chars <= 0:
        return 0.0
    return float(sep_chars) / float(mix_chars)


def runtime_ratio_safe(sep_runtime: float, mix_runtime: float) -> float:
    """separated_runtime / mixed_runtime with safe zero-denominator handling."""
    if mix_runtime <= 0:
        return 0.0
    return float(sep_runtime) / float(mix_runtime)


def extract_metadata_features(window: dict[str, Any]) -> dict[str, float]:
    """Extract the 7 metadata features from an AISHELL-4 window dict.

    The window dict is expected to have the fields produced by
    ``rq1_aishell4_validation.py``:
    ``separated_runtime_sec``, ``mixed_runtime_sec``,
    ``separated_total_length``, ``mixed_text_length``,
    ``separated_text_per_speaker`` (a dict speaker_id -> text).
    """
    sep_rt = float(window.get("separated_runtime_sec", 0.0) or 0.0)
    mix_rt = float(window.get("mixed_runtime_sec", 0.0) or 0.0)
    sep_chars = int(window.get("separated_total_length", 0) or 0)
    mix_chars = int(window.get("mixed_text_length", 0) or 0)

    sep_per_speaker = window.get("separated_text_per_speaker", {}) or {}
    speaker_lengths = [len(str(v)) for v in sep_per_speaker.values()]
    active_lengths = [x for x in speaker_lengths if x > 0]
    num_active = len(active_lengths)
    avg_len = float(sum(active_lengths) / num_active) if num_active > 0 else 0.0
    entropy = shannon_entropy_nats(speaker_lengths)

    return {
        "runtime_ratio": runtime_ratio_safe(sep_rt, mix_rt),
        "sep_total_chars": float(sep_chars),
        "mix_total_chars": float(mix_chars),
        "char_ratio": char_ratio_safe(sep_chars, mix_chars),
        "num_active_speakers_sep": float(num_active),
        "avg_speaker_length_sep": avg_len,
        "length_entropy_speakers": entropy,
    }


# --------------------------------------------------------------- CART decision tree
class Node:
    """A single node in a CART decision tree."""
    __slots__ = (
        "feature", "threshold", "left", "right",
        "prediction", "is_leaf", "gain", "n_samples",
    )

    def __init__(self) -> None:
        self.feature: int = -1
        self.threshold: float = 0.0
        self.left: Node | None = None
        self.right: Node | None = None
        self.prediction: int = 0
        self.is_leaf: bool = True
        self.gain: float = 0.0
        self.n_samples: int = 0


class DecisionTree:
    """CART decision tree with weighted Gini impurity (matches RQ28).

    Recursive binary split: at each node, find the feature+threshold that
    maximally reduces weighted Gini impurity. Stop at max_depth,
    min_samples_split, or purity.
    """

    def __init__(self, max_depth: int = MAX_DEPTH, min_samples_split: int = MIN_SAMPLES_SPLIT) -> None:
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.root: Node | None = None
        self.feature_importances_: np.ndarray | None = None
        self.n_classes: int = 0
        self.n_total: int = 0

    def fit(self, X: np.ndarray, y: np.ndarray, w: np.ndarray, n_classes: int) -> "DecisionTree":
        self.n_classes = n_classes
        self.n_total = len(y)
        self.feature_importances_ = np.zeros(X.shape[1])
        total_w = float(w.sum())
        if total_w <= 0:
            total_w = 1.0
        self.root = self._build(X, y, w, 0, total_w)
        s = self.feature_importances_.sum()
        if s > 0:
            self.feature_importances_ /= s
        return self

    def _best_split(
        self, X: np.ndarray, y: np.ndarray, w: np.ndarray, total_w: float
    ) -> tuple[int, float, float] | None:
        """Find the feature+threshold that maximally reduces weighted Gini impurity."""
        n, d = X.shape
        if n < 2:
            return None

        parent_class_w = np.bincount(y, weights=w, minlength=self.n_classes).astype(float)
        parent_gini = 1.0 - np.sum((parent_class_w / total_w) ** 2)

        best_gain = 0.0
        best_feature = -1
        best_threshold = 0.0

        for f in range(d):
            col = X[:, f]
            order = np.argsort(col, kind="quicksort")
            col_s = col[order]
            y_s = y[order]
            w_s = w[order]

            ohw = np.zeros((n, self.n_classes))
            ohw[np.arange(n), y_s] = w_s
            cum_cw = np.cumsum(ohw, axis=0)
            cum_w = np.cumsum(w_s)

            left_w = cum_w[:-1]
            right_w = total_w - left_w

            left_cw = cum_cw[:-1]
            right_cw = parent_class_w - left_cw

            lw_safe = np.where(left_w > 0, left_w, 1.0)
            rw_safe = np.where(right_w > 0, right_w, 1.0)

            left_gini = 1.0 - np.sum((left_cw / lw_safe[:, None]) ** 2, axis=1)
            right_gini = 1.0 - np.sum((right_cw / rw_safe[:, None]) ** 2, axis=1)

            weighted_gini = (left_w * left_gini + right_w * right_gini) / total_w
            gain = parent_gini - weighted_gini

            valid = col_s[:-1] < col_s[1:]
            gain = np.where(valid, gain, -1.0)

            idx = int(np.argmax(gain))
            if gain[idx] > best_gain:
                best_gain = float(gain[idx])
                best_feature = f
                best_threshold = float((col_s[idx] + col_s[idx + 1]) / 2.0)

        if best_feature < 0 or best_gain <= 0:
            return None
        return best_feature, best_threshold, best_gain

    def _build(
        self, X: np.ndarray, y: np.ndarray, w: np.ndarray, depth: int, total_w: float
    ) -> Node:
        n = len(y)
        node = Node()
        node.n_samples = n

        class_w = np.bincount(y, weights=w, minlength=self.n_classes)
        node.prediction = int(np.argmax(class_w))

        n_unique = len(np.unique(y))
        if depth >= self.max_depth or n < self.min_samples_split or n_unique <= 1:
            node.is_leaf = True
            return node

        result = self._best_split(X, y, w, total_w)
        if result is None:
            node.is_leaf = True
            return node

        f, threshold, gain = result
        left_mask = X[:, f] <= threshold
        n_left = int(left_mask.sum())
        n_right = n - n_left

        if n_left == 0 or n_right == 0:
            node.is_leaf = True
            return node

        node_w = float(w.sum())
        self.feature_importances_[f] += (node_w / total_w) * gain

        node.is_leaf = False
        node.feature = f
        node.threshold = threshold
        node.gain = gain
        node.left = self._build(X[left_mask], y[left_mask], w[left_mask], depth + 1, total_w)
        node.right = self._build(X[~left_mask], y[~left_mask], w[~left_mask], depth + 1, total_w)
        return node

    def predict_one(self, x: np.ndarray) -> int:
        node = self.root
        assert node is not None
        while not node.is_leaf:
            if x[node.feature] <= node.threshold:
                node = node.left
            else:
                node = node.right
            assert node is not None
        return node.prediction


# --------------------------------------------------------------- random forest
class RandomForest:
    """Bootstrap-aggregated CART decision trees with majority-vote prediction.

    Identical hyperparameters and protocol to RQ28: 100 trees, max_depth=10,
    sqrt inverse-frequency class weighting, standard bootstrap of n samples.
    """

    def __init__(
        self,
        n_trees: int = N_TREES,
        max_depth: int = MAX_DEPTH,
        min_samples_split: int = MIN_SAMPLES_SPLIT,
        class_weight: str = CLASS_WEIGHT,
        seed: int = SEED,
    ) -> None:
        self.n_trees = n_trees
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.class_weight = class_weight
        self.seed = seed
        self.trees: list[DecisionTree] = []
        self.feature_importances_: np.ndarray | None = None
        self.n_classes: int = 0

    def _compute_sample_weights(self, y: np.ndarray, n_classes: int) -> np.ndarray:
        n = len(y)
        if self.class_weight == "none":
            return np.ones(n)
        counts = np.bincount(y, minlength=n_classes).astype(float)
        counts = np.where(counts < 1, 1.0, counts)
        if self.class_weight == "full":
            inv_freq = 1.0 / counts
        else:  # sqrt
            inv_freq = 1.0 / np.sqrt(counts)
        sw = inv_freq[y]
        sw = sw * (n / sw.sum())  # normalize so weights sum to n
        return sw

    def fit(self, X: np.ndarray, y: np.ndarray, n_classes: int) -> "RandomForest":
        rng = np.random.default_rng(self.seed)
        n, d = X.shape
        self.n_classes = n_classes
        self.feature_importances_ = np.zeros(d)
        sample_w = self._compute_sample_weights(y, n_classes)

        for _ in range(self.n_trees):
            indices = rng.integers(0, n, size=n)
            X_bs = X[indices]
            y_bs = y[indices]
            w_bs = sample_w[indices]
            tree = DecisionTree(
                max_depth=self.max_depth,
                min_samples_split=self.min_samples_split,
            )
            tree.fit(X_bs, y_bs, w_bs, n_classes)
            self.trees.append(tree)
            self.feature_importances_ += tree.feature_importances_

        total = self.feature_importances_.sum()
        if total > 0:
            self.feature_importances_ /= total
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        n = X.shape[0]
        votes = np.zeros((n, self.n_classes), dtype=int)
        for tree in self.trees:
            for i in range(n):
                votes[i, tree.predict_one(X[i])] += 1
        return np.argmax(votes, axis=1)


# --------------------------------------------------------------- data loading
def load_tracks() -> list[dict[str, Any]]:
    """Load per-track data from RQ23's CSV. This is the EXACT same feature
    matrix and mode labels used by RQ23 and RQ28 -- no recomputation."""
    tracks: list[dict[str, Any]] = []
    with RQ23_CSV.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            tracks.append({
                "dataset": r["dataset"],
                "track_id": r["track_id"],
                "true_mode": r["true_mode"],
                "rq23_predicted_mode": r["predicted_mode"],
                "cr": float(r["cr"]),
                "lang_id_entropy": float(r["lang_id_entropy"]),
                "length_ratio": float(r["length_ratio"]),
                "content_similarity": float(r["content_similarity"]),
                "num_speakers": float(r["num_speakers"]),
            })
    return tracks


def load_aishell4_windows() -> dict[int, dict[str, Any]]:
    """Load AISHELL-4 validation windows, keyed by window_id."""
    data = json.loads(A4_JSON.read_text(encoding="utf-8"))
    return {int(w["window_id"]): w for w in data["windows"]}


def build_feature_matrix(
    tracks: list[dict[str, Any]],
    a4_windows: dict[int, dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """Build the 13-feature matrix (5 original + 7 metadata + 1 has_metadata).

    For AISHELL-4 tracks, the 7 metadata features are extracted from the
    matching window. For gold tracks, metadata features are 0.0 and
    has_metadata = 0.0.

    Returns (X, y, enriched_tracks) where enriched_tracks extends the input
    track dicts with the extracted metadata features and has_metadata.
    """
    enriched: list[dict[str, Any]] = []
    X_rows: list[list[float]] = []
    y_list: list[int] = []

    for t in tracks:
        row = dict(t)  # copy
        has_metadata = 0.0
        meta: dict[str, float] = {k: 0.0 for k in METADATA_FEATURES}

        if t["dataset"] == "aishell4":
            try:
                wid = int(t["track_id"])
            except (ValueError, TypeError):
                wid = -1
            if wid in a4_windows:
                meta = extract_metadata_features(a4_windows[wid])
                has_metadata = 1.0

        for k in METADATA_FEATURES:
            row[k] = meta[k]
        row["has_metadata"] = has_metadata
        enriched.append(row)

        feat_row = (
            [t[k] for k in ORIGINAL_FEATURES]
            + [meta[k] for k in METADATA_FEATURES]
            + [has_metadata]
        )
        X_rows.append([float(v) for v in feat_row])
        y_list.append(MODE_TO_IDX[t["true_mode"]])

    X = np.array(X_rows, dtype=float)
    y = np.array(y_list, dtype=int)
    return X, y, enriched


# --------------------------------------------------------------- LOO cross-validation
def loo_cross_validate(
    X: np.ndarray, y: np.ndarray, n_classes: int, seed: int = SEED
) -> np.ndarray:
    """Leave-one-out CV. For each held-out sample, train RF on the other n-1
    samples and predict the held-out. Returns array of predicted class indices."""
    n = len(y)
    preds = np.zeros(n, dtype=int)
    t0 = time.time()
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        X_tr, y_tr = X[mask], y[mask]
        X_hold = X[i:i + 1]
        rf = RandomForest(
            n_trees=N_TREES, max_depth=MAX_DEPTH,
            min_samples_split=MIN_SAMPLES_SPLIT,
            class_weight=CLASS_WEIGHT, seed=seed,
        )
        rf.fit(X_tr, y_tr, n_classes)
        preds[i] = int(rf.predict(X_hold)[0])
        if (i + 1) % 50 == 0 or i == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (n - i - 1) / rate
            print(f"  LOO fold {i+1}/{n}  elapsed={elapsed:.1f}s  eta={eta:.1f}s  rate={rate:.2f}fold/s")
    return preds


# --------------------------------------------------------------- metrics
def wilson_ci(correct: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n <= 0:
        return 0.0, 0.0, 0.0
    p = correct / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return p, max(0.0, centre - margin), min(1.0, centre + margin)


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> np.ndarray:
    cm = np.zeros((n_classes, n_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1
    return cm


def per_class_metrics(cm: np.ndarray) -> list[dict[str, Any]]:
    n = cm.shape[0]
    out = []
    for c in range(n):
        tp = int(cm[c, c])
        fp = int(cm[:, c].sum() - tp)
        fn = int(cm[c, :].sum() - tp)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        out.append({
            "class": MODES[c],
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "support": int(cm[c, :].sum()),
        })
    return out


def compute_aishell4_sensitivity(
    tracks: list[dict[str, Any]], predicted_modes: list[str]
) -> dict[str, Any]:
    """AISHELL-4 mode-routed sensitivity (task definition).

    Route to mixed if predicted_mode in {Mode_R, Mode_S, Diverse}.
    Sensitivity = (truly hallucinated AND predicted hallucinated) /
                  (truly hallucinated).
    """
    a4_halluc = [
        (t, pm) for t, pm in zip(tracks, predicted_modes)
        if t["dataset"] == "aishell4" and t["true_mode"] != "Non-hallucinated"
    ]
    n_halluc = len(a4_halluc)
    if n_halluc == 0:
        return {"sensitivity": 0.0, "tp": 0, "n_hallucinated": 0, "ci_95": [0.0, 0.0]}

    tp = sum(1 for t, pm in a4_halluc if pm != "Non-hallucinated")
    sens = tp / n_halluc
    _, lo, hi = wilson_ci(tp, n_halluc)
    return {
        "sensitivity": round(sens, 6),
        "tp": tp,
        "n_hallucinated": n_halluc,
        "ci_95": [round(lo, 6), round(hi, 6)],
    }


# --------------------------------------------------------------- main
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 72)
    print("RQ32: Feature-expanded classifier -- 13 features vs RQ28's 5")
    print("=" * 72)

    # --- Load data
    tracks = load_tracks()
    a4_windows = load_aishell4_windows()
    n_total = len(tracks)
    n_gold = sum(1 for t in tracks if t["dataset"] == "gold")
    n_a4 = sum(1 for t in tracks if t["dataset"] == "aishell4")
    n_a4_with_meta = sum(
        1 for t in tracks
        if t["dataset"] == "aishell4" and int(t["track_id"]) in a4_windows
    )
    print(f"\nLoaded {n_total} tracks from RQ23 CSV")
    print(f"  gold: {n_gold}, AISHELL-4: {n_a4} (with metadata: {n_a4_with_meta})")
    print(f"  AISHELL-4 windows available: {len(a4_windows)}")

    mode_counts = {m: 0 for m in MODES}
    for t in tracks:
        mode_counts[t["true_mode"]] += 1
    print(f"  mode counts: {mode_counts}")

    # --- Build feature matrix
    X, y, enriched = build_feature_matrix(tracks, a4_windows)
    n_classes = len(MODES)
    print(f"\nFeature matrix: X.shape={X.shape}, y.shape={y.shape}")
    print(f"  features ({len(ALL_FEATURES)}): {ALL_FEATURES}")

    # --- RQ23 baseline metrics (from CSV predictions, for validation & comparison)
    rq23_preds = np.array([MODE_TO_IDX[t["rq23_predicted_mode"]] for t in tracks], dtype=int)
    rq23_correct = int((rq23_preds == y).sum())
    rq23_acc, _, _ = wilson_ci(rq23_correct, n_total)
    rq23_cm = confusion_matrix(y, rq23_preds, n_classes)
    rq23_off_diag = int(rq23_cm.sum() - np.trace(rq23_cm))
    rq23_div_nh = int(rq23_cm[2, 3] + rq23_cm[3, 2])
    rq23_pred_modes = [MODES[p] for p in rq23_preds]
    rq23_sens = compute_aishell4_sensitivity(tracks, rq23_pred_modes)
    print(f"\nRQ23 baseline (linear, 5 features):")
    print(f"  LOO accuracy: {rq23_acc:.6f} ({rq23_correct}/{n_total})")
    print(f"  Off-diagonal: {rq23_off_diag} (Diverse<->Non-halluc: {rq23_div_nh})")
    print(f"  A4 sensitivity: {rq23_sens['sensitivity']:.6f} ({rq23_sens['tp']}/{rq23_sens['n_hallucinated']})")

    # --- Validate RQ23 baseline against RQ23 JSON
    rq23_json = json.loads(RQ23_JSON.read_text(encoding="utf-8"))
    assert abs(rq23_acc - rq23_json["loo_accuracy"]["accuracy"]) < 1e-4, \
        f"RQ23 accuracy mismatch: {rq23_acc} vs {rq23_json['loo_accuracy']['accuracy']}"
    print("  [OK] RQ23 baseline validated against JSON")

    # --- Random forest LOO-CV on expanded features
    print(f"\n--- Random Forest LOO-CV (13 features) ---")
    print(f"  n_trees={N_TREES}, max_depth={MAX_DEPTH}, min_samples_split={MIN_SAMPLES_SPLIT}")
    print(f"  class_weight={CLASS_WEIGHT}, seed={SEED}")
    t_start = time.time()
    y_pred = loo_cross_validate(X, y, n_classes, seed=SEED)
    t_elapsed = time.time() - t_start
    print(f"  LOO-CV completed in {t_elapsed:.1f}s ({t_elapsed/60:.1f} min)")

    # --- RF metrics
    rf_correct = int((y_pred == y).sum())
    rf_acc, rf_lo, rf_hi = wilson_ci(rf_correct, n_total)
    rf_cm = confusion_matrix(y, y_pred, n_classes)
    rf_off_diag = int(rf_cm.sum() - np.trace(rf_cm))
    rf_div_nh = int(rf_cm[2, 3] + rf_cm[3, 2])
    rf_class_metrics = per_class_metrics(rf_cm)
    rf_pred_modes = [MODES[p] for p in y_pred]
    rf_sens = compute_aishell4_sensitivity(tracks, rf_pred_modes)

    n_nonhalluc = int((y == MODE_TO_IDX["Non-hallucinated"]).sum())
    baseline_acc = n_nonhalluc / n_total

    print(f"\n--- RF Results (13 features) ---")
    print(f"  LOO accuracy: {rf_acc:.6f} ({rf_correct}/{n_total})  CI=[{rf_lo:.6f}, {rf_hi:.6f}]")
    print(f"  Majority baseline: {baseline_acc:.6f} ({n_nonhalluc}/{n_total})")
    print(f"  Off-diagonal: {rf_off_diag} (Diverse<->Non-halluc: {rf_div_nh})")
    print(f"  A4 sensitivity: {rf_sens['sensitivity']:.6f} ({rf_sens['tp']}/{rf_sens['n_hallucinated']})")
    print(f"\n  Confusion matrix (rows=true, cols=pred):")
    print(f"    {'':18s}  " + "  ".join(f"{m:13s}" for m in MODES))
    for i, m in enumerate(MODES):
        print(f"    {m:18s}  " + "  ".join(f"{rf_cm[i,j]:13d}" for j in range(n_classes)))

    # --- Feature importances (from full-data RF)
    print(f"\n--- Feature importances (full-data RF) ---")
    rf_full = RandomForest(
        n_trees=N_TREES, max_depth=MAX_DEPTH,
        min_samples_split=MIN_SAMPLES_SPLIT,
        class_weight=CLASS_WEIGHT, seed=SEED,
    )
    rf_full.fit(X, y, n_classes)
    fi = rf_full.feature_importances_
    fi_dict = {ALL_FEATURES[i]: round(float(fi[i]), 6) for i in range(len(ALL_FEATURES))}
    for k in sorted(fi_dict, key=lambda k: -fi_dict[k]):
        print(f"  {k:28s}  {fi_dict[k]:.6f}")

    # --- Hypothesis verdicts
    h32a_supported = rf_acc > RQ28_LOO_ACCURACY
    h32a_killed = rf_acc <= RQ28_LOO_ACCURACY
    h32b_supported = rf_sens["sensitivity"] > 0.90
    h32b_killed = rf_sens["sensitivity"] <= 0.90
    h32c_supported = rf_div_nh < RQ28_DIVERSE_NONHALLUC_OFFDIAG
    h32c_killed = rf_div_nh >= RQ28_DIVERSE_NONHALLUC_OFFDIAG

    print(f"\n--- Hypothesis verdicts ---")
    print(f"  H32a (acc > {RQ28_LOO_ACCURACY}): {'SUPPORTED' if h32a_supported else 'NOT SUPPORTED'}  (got {rf_acc:.6f})")
    print(f"  H32b (A4 sens > 0.90): {'SUPPORTED' if h32b_supported else 'NOT SUPPORTED'}  (got {rf_sens['sensitivity']:.6f})")
    print(f"  H32c (Diverse<->Non-halluc < {RQ28_DIVERSE_NONHALLUC_OFFDIAG}): {'SUPPORTED' if h32c_supported else 'NOT SUPPORTED'}  (got {rf_div_nh})")

    # --- Comparison deltas
    acc_delta_rq28 = rf_acc - RQ28_LOO_ACCURACY
    sens_delta_rq28 = rf_sens["sensitivity"] - RQ28_A4_SENSITIVITY
    offdiag_delta_rq28 = rf_off_diag - RQ28_OFF_DIAGONAL
    divnh_delta_rq28 = rf_div_nh - RQ28_DIVERSE_NONHALLUC_OFFDIAG

    # --- Write per-track predictions CSV
    per_track_csv = OUT_DIR / "feature_expanded_per_track_predictions.csv"
    with per_track_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["dataset", "track_id", "true_mode", "rq23_predicted_mode"]
            + ["rf32_predicted_mode"]
            + ORIGINAL_FEATURES
            + METADATA_FEATURES
            + [INDICATOR_FEATURE]
        )
        for t, pm in zip(enriched, rf_pred_modes):
            w.writerow(
                [t["dataset"], t["track_id"], t["true_mode"], t["rq23_predicted_mode"], pm]
                + [t[k] for k in ORIGINAL_FEATURES]
                + [t[k] for k in METADATA_FEATURES]
                + [t[INDICATOR_FEATURE]]
            )

    # --- Write summary CSV
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "rq23_linear_5f", "rq28_rf_5f", "rq32_rf_13f", "delta_vs_rq28"])
        w.writerow(["loo_accuracy", round(rq23_acc, 6), RQ28_LOO_ACCURACY, round(rf_acc, 6), round(acc_delta_rq28, 6)])
        w.writerow(["loo_accuracy_correct", rq23_correct, "", rf_correct, ""])
        w.writerow(["wilson_ci_lo", "", "", round(rf_lo, 6), ""])
        w.writerow(["wilson_ci_hi", "", "", round(rf_hi, 6), ""])
        w.writerow(["majority_baseline", round(baseline_acc, 6), round(baseline_acc, 6), round(baseline_acc, 6), ""])
        w.writerow(["off_diagonal_total", rq23_off_diag, RQ28_OFF_DIAGONAL, rf_off_diag, offdiag_delta_rq28])
        w.writerow(["off_diagonal_diverse_nonhalluc", rq23_div_nh, RQ28_DIVERSE_NONHALLUC_OFFDIAG, rf_div_nh, divnh_delta_rq28])
        w.writerow(["a4_sensitivity_task_def", rq23_sens["sensitivity"], RQ28_A4_SENSITIVITY, rf_sens["sensitivity"], round(sens_delta_rq28, 6)])
        for f in ALL_FEATURES:
            w.writerow([f"feature_importance_{f}", "", "", fi_dict[f], ""])

    # --- Write JSON
    results: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ32: Feature expansion for Diverse<->Non-hallucinated classification",
        "closes_issue": 939,
        "method": (
            "reanalysis only (no Whisper / no ASR run); loads the EXACT same "
            "per-track feature matrix and mode labels from RQ23's "
            "mode_classifier_results.csv (677 tracks), augments the 5 original "
            "transcript features with 7 metadata features extracted from the "
            "AISHELL-4 validation windows (runtime_ratio, sep_total_chars, "
            "mix_total_chars, char_ratio, num_active_speakers_sep, "
            "avg_speaker_length_sep, length_entropy_speakers) plus a "
            "has_metadata binary indicator (0 for gold, 1 for AISHELL-4), and "
            "trains a numpy-only random forest identical to RQ28 (100 trees, "
            "max_depth=10, sqrt class weighting, LOO-CV)."
        ),
        "source_data": {
            "rq23_csv": str(RQ23_CSV.relative_to(PROJECT_ROOT)),
            "aishell4_json": str(A4_JSON.relative_to(PROJECT_ROOT)),
        },
        "classifier": {
            "model": "random forest (CART decision trees + bootstrap aggregation)",
            "implementation": "numpy only (no sklearn), identical to RQ28",
            "n_trees": N_TREES,
            "max_depth": MAX_DEPTH,
            "min_samples_split": MIN_SAMPLES_SPLIT,
            "split_criterion": "weighted Gini impurity",
            "class_weight": CLASS_WEIGHT,
            "class_weight_note": (
                "sqrt inverse-frequency sample weights in Gini computation, "
                "matching RQ23/RQ28. Weights computed per training fold."
            ),
            "bootstrap": "n samples drawn with replacement from n (standard bootstrap)",
            "prediction": "majority vote across trees",
            "cv": "leave-one-out (677 folds)",
            "seed": SEED,
            "features": ALL_FEATURES,
            "original_features": ORIGINAL_FEATURES,
            "metadata_features": METADATA_FEATURES,
            "indicator_feature": INDICATOR_FEATURE,
            "n_features": len(ALL_FEATURES),
            "n_classes": len(MODES),
            "runtime_seconds": round(t_elapsed, 1),
        },
        "counts": {
            "total_tracks": n_total,
            "gold_tracks": n_gold,
            "aishell4_tracks": n_a4,
            "aishell4_with_metadata": n_a4_with_meta,
            "aishell4_hallucinated": rf_sens["n_hallucinated"],
            "mode_counts": mode_counts,
        },
        "metadata_feature_extraction": {
            "runtime_ratio": "separated_runtime_sec / mixed_runtime_sec (0 if mix runtime is 0)",
            "sep_total_chars": "separated_total_length from AISHELL-4 window",
            "mix_total_chars": "mixed_text_length from AISHELL-4 window",
            "char_ratio": "sep_total_chars / mix_total_chars (0 if mix_total_chars is 0)",
            "num_active_speakers_sep": "count of non-empty speaker segments in separated_text_per_speaker",
            "avg_speaker_length_sep": "mean char length of non-empty speaker segments (0 if none)",
            "length_entropy_speakers": "Shannon entropy (nats, base e) of non-zero per-speaker length distribution (0 if < 2 active speakers)",
            "has_metadata": "1.0 for AISHELL-4 tracks, 0.0 for gold tracks (metadata features set to 0.0 for gold)",
            "note": (
                "For gold tracks, all 7 metadata features are 0.0 and "
                "has_metadata=0.0. The RF must learn to ignore the metadata "
                "block for gold tracks and rely on the 5 original features."
            ),
        },
        "hypotheses": {
            "H32a": {
                "statement": f"Expanded-feature RF LOO accuracy > {RQ28_LOO_ACCURACY} (RQ28 5-feature RF)",
                "kill_criterion": f"accuracy <= {RQ28_LOO_ACCURACY}",
                "rf32_accuracy": round(rf_acc, 6),
                "rq28_accuracy": RQ28_LOO_ACCURACY,
                "rq23_accuracy": round(rq23_acc, 6),
                "supported": h32a_supported,
                "killed": h32a_killed,
            },
            "H32b": {
                "statement": "AISHELL-4 mode-routed sensitivity > 90%",
                "kill_criterion": "sensitivity <= 90%",
                "rf32_sensitivity": rf_sens["sensitivity"],
                "rf32_tp": rf_sens["tp"],
                "rf32_n_hallucinated": rf_sens["n_hallucinated"],
                "rq28_sensitivity": RQ28_A4_SENSITIVITY,
                "rq23_sensitivity": rq23_sens["sensitivity"],
                "supported": h32b_supported,
                "killed": h32b_killed,
            },
            "H32c": {
                "statement": f"Diverse<->Non-hallucinated off-diagonal < {RQ28_DIVERSE_NONHALLUC_OFFDIAG} (RQ28)",
                "kill_criterion": f"off-diagonal >= {RQ28_DIVERSE_NONHALLUC_OFFDIAG}",
                "rf32_diverse_nonhalluc_offdiag": rf_div_nh,
                "rq28_diverse_nonhalluc_offdiag": RQ28_DIVERSE_NONHALLUC_OFFDIAG,
                "rq23_diverse_nonhalluc_offdiag": rq23_div_nh,
                "supported": h32c_supported,
                "killed": h32c_killed,
            },
        },
        "loo_accuracy": {
            "correct": rf_correct,
            "n": n_total,
            "accuracy": round(rf_acc, 6),
            "wilson_ci_95": [round(rf_lo, 6), round(rf_hi, 6)],
            "majority_class_baseline": round(baseline_acc, 6),
            "beats_baseline": rf_acc > baseline_acc,
        },
        "confusion_matrix": {
            "row_order": MODES,
            "col_order": MODES,
            "matrix": rf_cm.tolist(),
            "off_diagonal": rf_off_diag,
            "diverse_nonhalluc_offdiag": rf_div_nh,
        },
        "per_class_metrics": rf_class_metrics,
        "aishell4_mode_routed_sensitivity": {
            "description": (
                "route to mixed if predicted_mode in {Mode_R, Mode_S, Diverse}; "
                "sensitivity = (truly hallucinated AND predicted hallucinated) / "
                "(truly hallucinated)"
            ),
            "rf32_sensitivity": rf_sens["sensitivity"],
            "rf32_tp": rf_sens["tp"],
            "rf32_ci_95": rf_sens["ci_95"],
            "rq28_sensitivity": RQ28_A4_SENSITIVITY,
            "rq23_sensitivity": rq23_sens["sensitivity"],
        },
        "feature_importances": fi_dict,
        "comparison_to_rq28": {
            "accuracy_delta": round(acc_delta_rq28, 6),
            "a4_sensitivity_delta": round(sens_delta_rq28, 6),
            "off_diagonal_delta": offdiag_delta_rq28,
            "diverse_nonhalluc_offdiag_delta": divnh_delta_rq28,
            "rq28_loo_accuracy": RQ28_LOO_ACCURACY,
            "rf32_loo_accuracy": round(rf_acc, 6),
            "rq28_off_diagonal": RQ28_OFF_DIAGONAL,
            "rf32_off_diagonal": rf_off_diag,
            "rq28_diverse_nonhalluc_offdiag": RQ28_DIVERSE_NONHALLUC_OFFDIAG,
            "rf32_diverse_nonhalluc_offdiag": rf_div_nh,
            "rq28_a4_sensitivity": RQ28_A4_SENSITIVITY,
            "rf32_a4_sensitivity": rf_sens["sensitivity"],
        },
        "comparison_to_rq23": {
            "accuracy_delta": round(rf_acc - rq23_acc, 6),
            "a4_sensitivity_delta": round(rf_sens["sensitivity"] - rq23_sens["sensitivity"], 6),
            "off_diagonal_delta": rf_off_diag - rq23_off_diag,
            "diverse_nonhalluc_offdiag_delta": rf_div_nh - rq23_div_nh,
        },
        "rq23_confusion_matrix_for_reference": {
            "row_order": MODES,
            "col_order": MODES,
            "matrix": rq23_cm.tolist(),
            "off_diagonal": rq23_off_diag,
            "diverse_nonhalluc_offdiag": rq23_div_nh,
        },
        "references": [
            "RQ23: PR #924, results/frontier/per_track_mode_classifier/ (linear, 5 features, 95.7% LOO)",
            "RQ28: PR #933, results/frontier/nonlinear_mode_classifier/ (RF, 5 features, 96.9% LOO, 17 Diverse<->Non-halluc off-diag)",
            "AISHELL-4: results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json",
        ],
    }
    OUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n--- Output files ---")
    print(f"  {OUT_CSV}")
    print(f"  {OUT_JSON}")
    print(f"  {per_track_csv}")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
