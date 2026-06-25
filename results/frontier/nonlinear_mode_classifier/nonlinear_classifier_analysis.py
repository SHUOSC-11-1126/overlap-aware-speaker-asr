"""RQ28: Non-linear mode classifier -- random forest to close the 13.5pp gap from RQ23.

RQ23 (PR #924) built a linear multinomial logistic regression on 5 transcript features
(cr, lang_id_entropy, length_ratio, content_similarity, num_speakers) to classify tracks
into 4 modes (Mode_R, Mode_S, Diverse, Non-hallucinated). It achieved 95.7% LOO accuracy
on 677 tracks (600 gold + 77 AISHELL-4) but only 81.1% mode-routed sensitivity on
AISHELL-4. The load-bearing confusion is Diverse <-> Non-hallucinated (29 total
off-diagonal errors, 17 directly between those two classes).

RQ26 (PR #930) confirmed the bottleneck is classifier accuracy, not routing. The open
question: is the confusion fundamental (overlapping features) or an artifact of the
linear classifier?

This study implements a random forest (CART + bootstrap aggregation, numpy only) on the
EXACT same feature matrix and mode labels as RQ23, using the same LOO-CV protocol, to
test whether a non-linear classifier can close the gap.

Hypotheses (pre-registered)
---------------------------
- H28a: RF LOO accuracy > 95.7% on the combined 677-track set. Kill: <= 95.7%.
- H28b: RF AISHELL-4 mode-routed sensitivity > 90%. Kill: <= 90%.
  Sensitivity = (truly hallucinated AND predicted hallucinated) / (truly hallucinated),
  where "predicted hallucinated" = predicted_mode in {Mode_R, Mode_S, Diverse}.
- H28c: Total off-diagonal errors decrease by >= 50% (from 29 to <= 14). Kill: > 14.

Label: experimental/frontier. Closes #932.
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
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "nonlinear_mode_classifier"
OUT_CSV = OUT_DIR / "nonlinear_classifier_results.csv"
OUT_JSON = OUT_DIR / "nonlinear_classifier_results.json"

# --------------------------------------------------------------- constants
MODES = ["Mode_R", "Mode_S", "Diverse", "Non-hallucinated"]
MODE_TO_IDX = {m: i for i, m in enumerate(MODES)}
FEATURES = ["cr", "lang_id_entropy", "length_ratio", "content_similarity", "num_speakers"]

SEED = 42
N_TREES = 100
MAX_DEPTH = 10
MIN_SAMPLES_SPLIT = 5
CLASS_WEIGHT = "sqrt"  # matches RQ23's sqrt inverse-frequency protocol

# RQ23 thresholds (for mode_routed_detect reference computation)
GOLD_CR_THRESHOLD = 15.818182
LANG_ID_THRESHOLD = 0.409073
EPS = 1e-9

# RQ23 baseline numbers (for comparison)
RQ23_LOO_ACCURACY = 0.957164
RQ23_OFF_DIAGONAL = 29
RQ23_A4_SENSITIVITY_ORIGINAL = 0.810811  # mode_routed_detect definition


# --------------------------------------------------------------- data loading
def load_tracks() -> list[dict[str, Any]]:
    """Load per-track data from RQ23's CSV. This is the EXACT same feature matrix and
    mode labels used by RQ23 -- no recomputation."""
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
    """CART decision tree with Gini impurity and weighted samples.

    Recursive binary split: at each node, find the feature+threshold that maximally
    reduces weighted Gini impurity. Stop at max_depth, min_samples_split, or purity.
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
        """Find the feature+threshold that maximally reduces weighted Gini impurity.

        Returns (feature_index, threshold, gain) or None if no valid split exists.
        Uses cumulative class-weight sums for vectorized O(n * n_classes) evaluation
        of all candidate thresholds per feature.
        """
        n, d = X.shape
        if n < 2:
            return None

        # Parent class weights and Gini
        parent_class_w = np.bincount(y, weights=w, minlength=self.n_classes).astype(float)
        parent_gini = 1.0 - np.sum((parent_class_w / total_w) ** 2)

        best_gain = 0.0  # only accept strictly positive gain
        best_feature = -1
        best_threshold = 0.0

        for f in range(d):
            col = X[:, f]
            order = np.argsort(col, kind="quicksort")
            col_s = col[order]
            y_s = y[order]
            w_s = w[order]

            # One-hot weighted matrix -> cumulative class weights
            ohw = np.zeros((n, self.n_classes))
            ohw[np.arange(n), y_s] = w_s
            cum_cw = np.cumsum(ohw, axis=0)  # (n, n_classes)
            cum_w = np.cumsum(w_s)           # (n,)

            # Split at position i: left = [0..i], right = [i+1..n-1]
            # i ranges from 0 to n-2
            left_w = cum_w[:-1]              # (n-1,)
            right_w = total_w - left_w

            left_cw = cum_cw[:-1]            # (n-1, n_classes)
            right_cw = parent_class_w - left_cw

            # Guard against zero-weight sides
            lw_safe = np.where(left_w > 0, left_w, 1.0)
            rw_safe = np.where(right_w > 0, right_w, 1.0)

            left_gini = 1.0 - np.sum((left_cw / lw_safe[:, None]) ** 2, axis=1)
            right_gini = 1.0 - np.sum((right_cw / rw_safe[:, None]) ** 2, axis=1)

            weighted_gini = (left_w * left_gini + right_w * right_gini) / total_w
            gain = parent_gini - weighted_gini

            # Only valid where consecutive values differ
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

        # Weighted majority class
        class_w = np.bincount(y, weights=w, minlength=self.n_classes)
        node.prediction = int(np.argmax(class_w))

        # Stopping criteria
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

        # Feature importance: weighted impurity decrease
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
    """Bootstrap-aggregated CART decision trees with majority-vote prediction."""

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


# --------------------------------------------------------------- LOO cross-validation
def loo_cross_validate(
    X: np.ndarray, y: np.ndarray, n_classes: int, seed: int = SEED
) -> np.ndarray:
    """Leave-one-out CV. For each held-out sample, train RF on the other n-1 samples
    and predict the held-out. Returns array of predicted class indices."""
    n = len(y)
    preds = np.zeros(n, dtype=int)
    t0 = time.time()
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        X_tr, y_tr = X[mask], y[mask]
        X_hold = X[i:i + 1]
        # Use the same seed for each fold (deterministic bootstrap).
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


def mode_routed_detect_original(track: dict[str, Any], predicted_mode: str) -> bool:
    """RQ23's original mode_routed_detect: Mode R -> CR, Diverse -> lang-id,
    Mode S / Non-hallucinated -> not flagged. Returns True if flagged as hallucinated."""
    if predicted_mode == "Mode_R":
        return track["cr"] >= GOLD_CR_THRESHOLD - EPS
    if predicted_mode == "Diverse":
        return track["lang_id_entropy"] >= LANG_ID_THRESHOLD - EPS
    return False


def compute_aishell4_sensitivity(
    tracks: list[dict[str, Any]], predicted_modes: list[str], definition: str
) -> dict[str, Any]:
    """Compute AISHELL-4 mode-routed sensitivity.

    definition="task": route to mixed if predicted_mode in {Mode_R, Mode_S, Diverse}.
        Sensitivity = (truly hallucinated AND predicted hallucinated) / (truly hallucinated).
    definition="rq23_original": RQ23's mode_routed_detect with CR/lang-id thresholds.
    """
    a4_halluc = [
        (t, pm) for t, pm in zip(tracks, predicted_modes)
        if t["dataset"] == "aishell4" and t["true_mode"] != "Non-hallucinated"
    ]
    n_halluc = len(a4_halluc)
    if n_halluc == 0:
        return {"sensitivity": 0.0, "tp": 0, "n_hallucinated": 0, "ci_95": [0.0, 0.0]}

    if definition == "task":
        tp = sum(1 for t, pm in a4_halluc if pm != "Non-hallucinated")
    else:  # rq23_original
        tp = sum(1 for t, pm in a4_halluc if mode_routed_detect_original(t, pm))

    sens = tp / n_halluc
    _, lo, hi = wilson_ci(tp, n_halluc)
    return {
        "sensitivity": round(sens, 6),
        "tp": tp,
        "n_hallucinated": n_halluc,
        "ci_95": [round(lo, 6), round(hi, 6)],
        "definition": definition,
    }


# --------------------------------------------------------------- main
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 72)
    print("RQ28: Non-linear mode classifier -- random forest")
    print("=" * 72)

    # --- Load data (exact same feature matrix as RQ23)
    tracks = load_tracks()
    n_total = len(tracks)
    print(f"\nLoaded {n_total} tracks from RQ23 CSV")
    n_gold = sum(1 for t in tracks if t["dataset"] == "gold")
    n_a4 = sum(1 for t in tracks if t["dataset"] == "aishell4")
    print(f"  gold: {n_gold}, AISHELL-4: {n_a4}")

    # --- Build feature matrix and labels
    X = np.array([[t[k] for k in FEATURES] for t in tracks], dtype=float)
    y = np.array([MODE_TO_IDX[t["true_mode"]] for t in tracks], dtype=int)
    n_classes = len(MODES)

    mode_counts = {m: 0 for m in MODES}
    for t in tracks:
        mode_counts[t["true_mode"]] += 1
    print(f"  mode counts: {mode_counts}")

    # --- RQ23 baseline metrics (from CSV predictions, for validation & comparison)
    rq23_preds = np.array([MODE_TO_IDX[t["rq23_predicted_mode"]] for t in tracks], dtype=int)
    rq23_correct = int((rq23_preds == y).sum())
    rq23_acc, rq23_lo, rq23_hi = wilson_ci(rq23_correct, n_total)
    rq23_cm = confusion_matrix(y, rq23_preds, n_classes)
    rq23_off_diag = int(rq23_cm.sum() - np.trace(rq23_cm))
    rq23_div_nh = int(rq23_cm[2, 3] + rq23_cm[3, 2])  # Diverse <-> Non-hallucinated
    rq23_pred_modes = [MODES[p] for p in rq23_preds]
    rq23_sens_task = compute_aishell4_sensitivity(tracks, rq23_pred_modes, "task")
    rq23_sens_orig = compute_aishell4_sensitivity(tracks, rq23_pred_modes, "rq23_original")

    print(f"\nRQ23 baseline (from CSV):")
    print(f"  LOO accuracy: {rq23_acc:.6f} ({rq23_correct}/{n_total})")
    print(f"  Off-diagonal: {rq23_off_diag} (Diverse<->Non-halluc: {rq23_div_nh})")
    print(f"  A4 sensitivity (task def): {rq23_sens_task['sensitivity']:.6f} ({rq23_sens_task['tp']}/{rq23_sens_task['n_hallucinated']})")
    print(f"  A4 sensitivity (RQ23 orig): {rq23_sens_orig['sensitivity']:.6f} ({rq23_sens_orig['tp']}/{rq23_sens_orig['n_hallucinated']})")

    # Validate against RQ23 JSON
    rq23_json = json.loads(RQ23_JSON.read_text(encoding="utf-8"))
    assert abs(rq23_acc - rq23_json["loo_accuracy"]["accuracy"]) < 1e-4, \
        f"RQ23 accuracy mismatch: {rq23_acc} vs {rq23_json['loo_accuracy']['accuracy']}"
    assert rq23_off_diag == rq23_json["confusion_matrix"]["off_diagonal"], \
        f"RQ23 off-diagonal mismatch: {rq23_off_diag} vs {rq23_json['confusion_matrix']['off_diagonal']}"
    print("  [OK] RQ23 baseline validated against JSON")

    # --- Random forest LOO-CV
    print(f"\n--- Random Forest LOO-CV ---")
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
    rf_sens_task = compute_aishell4_sensitivity(tracks, rf_pred_modes, "task")
    rf_sens_orig = compute_aishell4_sensitivity(tracks, rf_pred_modes, "rq23_original")

    # Majority-class baseline
    n_nonhalluc = int((y == MODE_TO_IDX["Non-hallucinated"]).sum())
    baseline_acc = n_nonhalluc / n_total

    print(f"\n--- RF Results ---")
    print(f"  LOO accuracy: {rf_acc:.6f} ({rf_correct}/{n_total})  CI=[{rf_lo:.6f}, {rf_hi:.6f}]")
    print(f"  Majority baseline: {baseline_acc:.6f} ({n_nonhalluc}/{n_total})")
    print(f"  Off-diagonal: {rf_off_diag} (Diverse<->Non-halluc: {rf_div_nh})")
    print(f"  A4 sensitivity (task def): {rf_sens_task['sensitivity']:.6f} ({rf_sens_task['tp']}/{rf_sens_task['n_hallucinated']})")
    print(f"  A4 sensitivity (RQ23 orig): {rf_sens_orig['sensitivity']:.6f} ({rf_sens_orig['tp']}/{rf_sens_orig['n_hallucinated']})")
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
    fi_dict = {FEATURES[i]: round(float(fi[i]), 6) for i in range(len(FEATURES))}
    for k in sorted(fi_dict, key=lambda k: -fi_dict[k]):
        print(f"  {k:22s}  {fi_dict[k]:.6f}")

    # --- Hypothesis verdicts
    h28a_supported = rf_acc > RQ23_LOO_ACCURACY
    h28a_killed = rf_acc <= RQ23_LOO_ACCURACY
    h28b_supported = rf_sens_task["sensitivity"] > 0.90
    h28b_killed = rf_sens_task["sensitivity"] <= 0.90
    h28c_supported = rf_off_diag <= 14  # >= 50% reduction from 29
    h28c_killed = rf_off_diag > 14

    print(f"\n--- Hypothesis verdicts ---")
    print(f"  H28a (acc > {RQ23_LOO_ACCURACY}): {'SUPPORTED' if h28a_supported else 'NOT SUPPORTED'}  (got {rf_acc:.6f})")
    print(f"  H28b (A4 sens > 0.90): {'SUPPORTED' if h28b_supported else 'NOT SUPPORTED'}  (got {rf_sens_task['sensitivity']:.6f})")
    print(f"  H28c (off-diag <= 14): {'SUPPORTED' if h28c_supported else 'NOT SUPPORTED'}  (got {rf_off_diag})")

    # --- Comparison to RQ23
    acc_delta = rf_acc - rq23_acc
    sens_delta = rf_sens_task["sensitivity"] - rq23_sens_task["sensitivity"]
    offdiag_delta = rf_off_diag - rq23_off_diag

    # --- Write per-track predictions CSV
    per_track_csv = OUT_DIR / "nonlinear_classifier_per_track_predictions.csv"
    with per_track_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["dataset", "track_id", "true_mode", "rq23_predicted_mode",
                     "rf_predicted_mode", "cr", "lang_id_entropy", "length_ratio",
                     "content_similarity", "num_speakers"])
        for t, pm in zip(tracks, rf_pred_modes):
            w.writerow([
                t["dataset"], t["track_id"], t["true_mode"],
                t["rq23_predicted_mode"], pm,
                t["cr"], t["lang_id_entropy"], t["length_ratio"],
                t["content_similarity"], t["num_speakers"],
            ])

    # --- Write summary CSV
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "rq23_linear", "rf_nonlinear", "delta"])
        w.writerow(["loo_accuracy", round(rq23_acc, 6), round(rf_acc, 6), round(acc_delta, 6)])
        w.writerow(["loo_accuracy_correct", rq23_correct, rf_correct, rf_correct - rq23_correct])
        w.writerow(["wilson_ci_lo", round(rq23_lo, 6), round(rf_lo, 6), ""])
        w.writerow(["wilson_ci_hi", round(rq23_hi, 6), round(rf_hi, 6), ""])
        w.writerow(["majority_baseline", round(baseline_acc, 6), round(baseline_acc, 6), ""])
        w.writerow(["off_diagonal_total", rq23_off_diag, rf_off_diag, offdiag_delta])
        w.writerow(["off_diagonal_diverse_nonhalluc", rq23_div_nh, rf_div_nh, rf_div_nh - rq23_div_nh])
        w.writerow(["a4_sensitivity_task_def", rq23_sens_task["sensitivity"], rf_sens_task["sensitivity"], round(sens_delta, 6)])
        w.writerow(["a4_sensitivity_rq23_orig", rq23_sens_orig["sensitivity"], rf_sens_orig["sensitivity"], ""])
        for i, f in enumerate(FEATURES):
            w.writerow([f"feature_importance_{f}", "", fi_dict[f], ""])

    # --- Write JSON
    results: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ28: Non-linear mode classifier -- random forest to close the 13.5pp gap from RQ23",
        "closes_issue": 932,
        "method": (
            "reanalysis only (no Whisper / no ASR run); loads the EXACT same per-track "
            "feature matrix and mode labels from RQ23's mode_classifier_results.csv and "
            "trains a numpy-only random forest (CART + bootstrap aggregation) with the "
            "same LOO-CV protocol. No features are recomputed."
        ),
        "source_data": str(RQ23_CSV.relative_to(PROJECT_ROOT)),
        "classifier": {
            "model": "random forest (CART decision trees + bootstrap aggregation)",
            "implementation": "numpy only (no sklearn)",
            "n_trees": N_TREES,
            "max_depth": MAX_DEPTH,
            "min_samples_split": MIN_SAMPLES_SPLIT,
            "split_criterion": "weighted Gini impurity",
            "class_weight": CLASS_WEIGHT,
            "class_weight_note": (
                "sqrt inverse-frequency sample weights in Gini computation, matching "
                "RQ23's linear classifier protocol. Weights are computed per training "
                "fold (no leakage from held-out sample)."
            ),
            "bootstrap": "n samples drawn with replacement from n (standard bootstrap)",
            "prediction": "majority vote across trees",
            "cv": "leave-one-out (677 folds)",
            "seed": SEED,
            "features": FEATURES,
            "n_features": len(FEATURES),
            "n_classes": len(MODES),
            "runtime_seconds": round(t_elapsed, 1),
        },
        "counts": {
            "total_tracks": n_total,
            "gold_tracks": n_gold,
            "aishell4_tracks": n_a4,
            "aishell4_hallucinated": rq23_sens_task["n_hallucinated"],
            "mode_counts": mode_counts,
        },
        "hypotheses": {
            "H28a": {
                "statement": f"RF LOO accuracy > {RQ23_LOO_ACCURACY} (RQ23 linear baseline)",
                "kill_criterion": f"accuracy <= {RQ23_LOO_ACCURACY}",
                "rf_accuracy": round(rf_acc, 6),
                "rq23_accuracy": round(rq23_acc, 6),
                "supported": h28a_supported,
                "killed": h28a_killed,
            },
            "H28b": {
                "statement": "RF AISHELL-4 mode-routed sensitivity > 90%",
                "kill_criterion": "sensitivity <= 90%",
                "rf_sensitivity": rf_sens_task["sensitivity"],
                "rf_tp": rf_sens_task["tp"],
                "rf_n_hallucinated": rf_sens_task["n_hallucinated"],
                "rq23_sensitivity": rq23_sens_task["sensitivity"],
                "supported": h28b_supported,
                "killed": h28b_killed,
            },
            "H28c": {
                "statement": "Total off-diagonal errors decrease by >= 50% (from 29 to <= 14)",
                "kill_criterion": "off-diagonal > 14",
                "rf_off_diagonal": rf_off_diag,
                "rq23_off_diagonal": rq23_off_diag,
                "rf_diverse_nonhalluc_offdiag": rf_div_nh,
                "rq23_diverse_nonhalluc_offdiag": rq23_div_nh,
                "supported": h28c_supported,
                "killed": h28c_killed,
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
            "task_definition": {
                "description": (
                    "route to mixed if predicted_mode in {Mode_R, Mode_S, Diverse}; "
                    "sensitivity = (truly hallucinated AND predicted hallucinated) / "
                    "(truly hallucinated)"
                ),
                "rf_sensitivity": rf_sens_task["sensitivity"],
                "rf_tp": rf_sens_task["tp"],
                "rf_ci_95": rf_sens_task["ci_95"],
                "rq23_sensitivity": rq23_sens_task["sensitivity"],
                "rq23_tp": rq23_sens_task["tp"],
            },
            "rq23_original_definition": {
                "description": (
                    "RQ23's mode_routed_detect: Mode R -> CR >= 15.818, Diverse -> "
                    "lang_id >= 0.409, Mode S / Non-hallucinated -> not flagged"
                ),
                "rf_sensitivity": rf_sens_orig["sensitivity"],
                "rf_tp": rf_sens_orig["tp"],
                "rq23_sensitivity": rq23_sens_orig["sensitivity"],
                "rq23_tp": rq23_sens_orig["tp"],
            },
        },
        "feature_importances": fi_dict,
        "comparison_to_rq23": {
            "accuracy_delta": round(acc_delta, 6),
            "a4_sensitivity_delta_task_def": round(sens_delta, 6),
            "off_diagonal_delta": offdiag_delta,
            "diverse_nonhalluc_offdiag_delta": rf_div_nh - rq23_div_nh,
            "rq23_loo_accuracy": round(rq23_acc, 6),
            "rf_loo_accuracy": round(rf_acc, 6),
            "rq23_off_diagonal": rq23_off_diag,
            "rf_off_diagonal": rf_off_diag,
            "rq23_a4_sensitivity_task": rq23_sens_task["sensitivity"],
            "rf_a4_sensitivity_task": rf_sens_task["sensitivity"],
        },
        "rq23_confusion_matrix_for_reference": {
            "row_order": MODES,
            "col_order": MODES,
            "matrix": rq23_cm.tolist(),
            "off_diagonal": rq23_off_diag,
        },
        "references": [
            "RQ23: PR #924, results/frontier/per_track_mode_classifier/",
            "RQ26: PR #930 (confirmed bottleneck is classifier accuracy, not routing)",
            "RQ21: PR #917 (CR + lang-id detector comparison, threshold calibration)",
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
