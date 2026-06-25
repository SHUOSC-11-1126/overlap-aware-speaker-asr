"""RQ23: Per-track mode classifier — transcript-feature routing without a dataset prior.

RQ21 (PR #917) showed that CR and language-id entropy are complementary detectors:
CR dominates on gold's repetitive hallucination (Mode R, 100% sensitivity), lang-id
dominates on AISHELL-4's diverse hallucination (94.6% sensitivity). A dataset-aware
switch achieved 95.2% combined sensitivity but REQUIRES knowing the dataset a priori.

This study asks: can a per-track mode classifier (Mode R / Mode S / Diverse /
Non-hallucinated) route each track to the right detector using ONLY transcript
features, with no dataset prior? A multinomial logistic regression (softmax + L2,
numpy only) is trained with leave-one-out cross-validation on 5 features computed
from stored transcripts. A mode-routed detector then maps each predicted mode to a
detector (Mode R -> CR, Diverse -> lang-id, Mode S -> unresolvable, Non-hallucinated
-> no detection) and sensitivity is measured per dataset.

Hypotheses
----------
- H23a: per-track mode classifier achieves > 80% accuracy (LOO) on 4-class task.
  Kill: accuracy <= 70%.
- H23b: mode-routed detector achieves > 90% sensitivity on both gold and AISHELL-4
  without a dataset prior. Kill: sensitivity <= 90% on either.
- H23c: confusion matrix reveals confusable modes. Kill: confusion matrix is diagonal.

Label: experimental/frontier. Closes #921.
"""
from __future__ import annotations

import csv
import json
import math
import unicodedata
import zlib
from pathlib import Path
from typing import Any

import numpy as np

# --------------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "per_track_mode_classifier"
GOLD_CSV = (
    PROJECT_ROOT / "results" / "frontier" / "gold_detector_comparison" / "comparison_results.csv"
)
GOLD_TEXT_JSON = (
    PROJECT_ROOT / "results" / "frontier" / "gold_detector_comparison" / "gold_track_texts.json"
)
AISHELL4_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_CSV = OUT_DIR / "mode_classifier_results.csv"
OUT_JSON = OUT_DIR / "mode_classifier_results.json"

# --------------------------------------------------------------- thresholds
GOLD_CR_THRESHOLD = 15.818182      # gold-calibrated CR threshold (RQ21, 100% spec)
LANG_ID_THRESHOLD = 0.409073      # AISHELL-4-calibrated lang-id threshold (RQ21, 92.5% spec)
CR_MODE_THRESHOLD = 2.4           # Whisper compression_ratio_threshold (Mode R boundary)
AISHELL4_CPWER_HALLUC = 1.0       # cpWER > 1.0 => hallucinated (AISHELL-4)
N_BOOT = 10000
SEED = 42
EPS = 1e-9

# Mode class indices (fixed ordering for confusion matrix)
MODES = ["Mode_R", "Mode_S", "Diverse", "Non-hallucinated"]
MODE_TO_IDX = {m: i for i, m in enumerate(MODES)}

# Classifier hyper-parameters
LR = 0.5
N_STEPS = 3000
L2 = 0.01
CLASS_WEIGHT = "sqrt"  # inverse-frequency rebalancing: "sqrt" (mild) or "full" or "none"


# ----------------------------------------------------------------- CR primitive
def compression_ratio(text: str) -> float:
    """Whisper-style compression ratio: len(utf8 bytes) / len(zlib-compressed bytes)."""
    if not text or not text.strip():
        return 0.0
    b = text.encode("utf-8")
    c = zlib.compress(b)
    return len(b) / len(c) if len(c) > 0 else 0.0


# ------------------------------------------------------------- script detection
def script_category(ch: str) -> str:
    """Map a character to a coarse Unicode script category (same as RQ13/RQ21)."""
    if ch.isspace():
        return "Space"
    name = unicodedata.name(ch, "")
    if not name:
        return "Other"
    first = name.split()[0]
    if first == "CJK":
        return "Han"
    if first == "LATIN" or "LATIN" in name:
        return "Latin"
    if first == "HIRAGANA":
        return "Hiragana"
    if first == "KATAKANA":
        return "Katakana"
    if first == "HANGUL":
        return "Hangul"
    if first == "CYRILLIC":
        return "Cyrillic"
    if first == "ARABIC":
        return "Arabic"
    if first == "GREEK":
        return "Greek"
    if first == "DIGIT":
        return "Digit"
    cat = unicodedata.category(ch)
    if cat.startswith("P") or cat.startswith("S"):
        return "Punct"
    return "Other"


def language_id_entropy(text: str) -> float:
    """Shannon entropy (bits) over the script-category distribution of the text."""
    if not text or not text.strip():
        return 0.0
    counts: dict[str, int] = {}
    for ch in text:
        sc = script_category(ch)
        counts[sc] = counts.get(sc, 0) + 1
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            h -= p * math.log2(p)
    return h


# --------------------------------------------------------------- token Jaccard
def char_token_set(text: str) -> set[str]:
    """Character-level token set (Chinese has no word boundaries)."""
    return {ch for ch in text if not ch.isspace()}


def jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard overlap between two token sets."""
    if not a and not b:
        return 1.0
    u = a | b
    if not u:
        return 0.0
    return len(a & b) / len(u)


# --------------------------------------------------------------- load gold tracks
def load_gold_tracks() -> list[dict[str, Any]]:
    """Load 600 gold tracks from comparison_results.csv plus gold_track_texts.json.

    The CSV supplies cr, lang_id_entropy, cer, hallucinated. The JSON supplies the
    raw separated text (sep1_text, sep2_text) so we can compute length_ratio and
    content_similarity. Gold has no stored mixed_text, so length_ratio is computed as
    this track's length over the two-speaker separated total (a within-condition
    proxy), and content_similarity is the Jaccard overlap between the two separated
    tracks (partner-track proxy). This asymmetry versus AISHELL-4 is documented as a
    limitation.
    """
    # Build text lookup by track_id from the JSON cache.
    cache = json.loads(GOLD_TEXT_JSON.read_text(encoding="utf-8"))
    text_by_track: dict[str, dict[str, str]] = {}
    for t in cache["tracks"]:
        track_base = f"{Path(t['con']).stem}_{Path(t['pro']).stem}_r{t['overlap_ratio']}"
        text_by_track[f"{track_base}_sep1"] = {
            "self_text": t["sep1_text"],
            "partner_text": t["sep2_text"],
            "sep1_text": t["sep1_text"],
            "sep2_text": t["sep2_text"],
        }
        text_by_track[f"{track_base}_sep2"] = {
            "self_text": t["sep2_text"],
            "partner_text": t["sep1_text"],
            "sep1_text": t["sep1_text"],
            "sep2_text": t["sep2_text"],
        }

    tracks: list[dict[str, Any]] = []
    with GOLD_CSV.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["dataset"] != "gold":
                continue
            tid = r["track_id"]
            txt = text_by_track.get(tid, {})
            self_text = txt.get("self_text", "")
            sep1 = txt.get("sep1_text", "")
            sep2 = txt.get("sep2_text", "")
            sep_total = len(sep1) + len(sep2)
            # Gold proxy: track's share of the two-speaker separated total.
            length_ratio = (len(self_text) / sep_total) if sep_total > 0 else 0.0
            # Gold proxy: overlap between this track and its partner.
            content_sim = jaccard(char_token_set(sep1), char_token_set(sep2))
            tracks.append({
                "dataset": "gold",
                "track_id": tid,
                "hallucinated": bool(int(r["hallucinated"])),
                "cr": float(r["cr"]),
                "lang_id_entropy": float(r["lang_id_entropy"]),
                "length_ratio": float(length_ratio),
                "content_similarity": float(content_sim),
                "num_speakers": 2,
                "cer": float(r["cer"]),
                "self_text": self_text,
            })
    return tracks


# ------------------------------------------------------------ load AISHELL-4 tracks
def load_aishell4_tracks() -> list[dict[str, Any]]:
    """Load 77 AISHELL-4 windows. Feature aggregation:

    - cr: computed on the CONCATENATED separated text (per RQ23 spec). Concatenation
      dilutes single-speaker repetition, so no AISHELL-4 window exceeds Whisper's
      cr > 2.4 Mode R boundary (the one max-cr > 2.4 window, #18, drops to 1.70 when
      concatenated). This keeps all AISHELL-4 hallucination in Mode S / Diverse.
    - lang_id_entropy: MAX across per-speaker separated texts (matching RQ21's
      calibration, where the 0.409 threshold was set on max-aggregated entropy). This
      reproduces RQ21's 2 / 35 Mode-S / Diverse split exactly (windows 22 and 30).

    length_ratio = separated_total_length / mixed_text_length.
    content_similarity = Jaccard(sep-concatenated, mixed). Hallucination label:
    always_separated_cpwer > 1.0."""
    data = json.loads(AISHELL4_JSON.read_text(encoding="utf-8"))
    tracks: list[dict[str, Any]] = []
    for w in data["windows"]:
        sep_cpwer = float(w["always_separated_cpwer"])
        sep_texts = w.get("separated_text_per_speaker", {})
        mixed_text = w.get("mixed_text", "")
        non_empty = [str(t) for t in sep_texts.values() if t and str(t).strip()]
        # Concatenated separated text (all speakers, in dict order).
        sep_concat = "".join(non_empty)
        sep_total_len = sum(len(t) for t in non_empty)
        mixed_len = len(mixed_text)
        # CR on concatenated text (per RQ23 spec).
        cr = compression_ratio(sep_concat)
        # lang_id_entropy: max across per-speaker texts (matching RQ21 calibration).
        ent_vals = [language_id_entropy(t) for t in non_empty]
        ent = max(ent_vals) if ent_vals else 0.0
        length_ratio = (sep_total_len / mixed_len) if mixed_len > 0 else 0.0
        content_sim = jaccard(char_token_set(sep_concat), char_token_set(mixed_text))
        halluc = sep_cpwer > AISHELL4_CPWER_HALLUC
        tracks.append({
            "dataset": "aishell4",
            "track_id": str(w["window_id"]),
            "hallucinated": bool(halluc),
            "cr": float(cr),
            "lang_id_entropy": float(ent),
            "length_ratio": float(length_ratio),
            "content_similarity": float(content_sim),
            "num_speakers": int(w.get("num_speakers", len(sep_texts))),
            "cer": sep_cpwer,
            "self_text": sep_concat,
        })
    return tracks


# --------------------------------------------------------------- mode labeling
def assign_mode(track: dict[str, Any]) -> str:
    """Assign a 4-class mode label from the pre-registered definitions.

    Mode R: hallucinated AND cr > 2.4 (gold's repetitive loops).
    Mode S: hallucinated AND lang_id_entropy < 0.409 AND cr < 2.4 (monoscript near-dup).
    Diverse: hallucinated AND lang_id_entropy >= 0.409.
    Non-hallucinated: not hallucinated.
    """
    if not track["hallucinated"]:
        return "Non-hallucinated"
    if track["cr"] > CR_MODE_THRESHOLD:
        return "Mode_R"
    if track["lang_id_entropy"] < LANG_ID_THRESHOLD:
        return "Mode_S"
    return "Diverse"


# ------------------------------------------------------- multinomial logistic reg
def softmax(z: np.ndarray) -> np.ndarray:
    """Numerically stable softmax along the last axis."""
    z = z - np.max(z, axis=1, keepdims=True)
    e = np.exp(z)
    return e / np.sum(e, axis=1, keepdims=True)


def one_hot(y: np.ndarray, n_classes: int) -> np.ndarray:
    oh = np.zeros((len(y), n_classes))
    oh[np.arange(len(y)), y] = 1.0
    return oh


def train_logreg(
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_classes: int,
    lr: float = LR,
    n_steps: int = N_STEPS,
    l2: float = L2,
    seed: int = SEED,
    class_weight: str = CLASS_WEIGHT,
) -> tuple[np.ndarray, np.ndarray]:
    """Train multinomial logistic regression (softmax + L2) via full-batch gradient
    descent. Returns (W, b) where W is (n_features, n_classes), b is (n_classes,).

    class_weight controls rebalancing for the 635 / 42 non-hallucinated / hallucinated
    imbalance: "sqrt" uses 1/sqrt(count) (mild), "full" uses 1/count (aggressive),
    "none" disables weighting. This does not change the model family — only the loss
    weighting."""
    n, d = X_train.shape
    rng = np.random.default_rng(seed)
    W = rng.normal(0, 0.01, size=(d, n_classes))
    b = np.zeros(n_classes)
    Y = one_hot(y_train, n_classes)
    if class_weight == "none":
        sample_w = np.ones(n)
    else:
        counts = np.bincount(y_train, minlength=n_classes).astype(float)
        counts = np.where(counts < 1, 1.0, counts)
        if class_weight == "full":
            inv_freq = 1.0 / counts
        else:  # sqrt
            inv_freq = 1.0 / np.sqrt(counts)
        sample_w = inv_freq[y_train]
        sample_w = sample_w * (n / sample_w.sum())  # normalize so weights sum to n
    sample_w = sample_w.reshape(-1, 1)
    for _ in range(n_steps):
        logits = X_train @ W + b
        P = softmax(logits)
        # Weighted gradient of cross-entropy + L2.
        grad_logits = (P - Y) * sample_w / n
        grad_W = X_train.T @ grad_logits + l2 * W
        grad_b = np.sum(grad_logits, axis=0)
        W -= lr * grad_W
        b -= lr * grad_b
    return W, b


def predict_logreg(X: np.ndarray, W: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.argmax(softmax(X @ W + b), axis=1)


def standardize_fit(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute mean and std (ddof=0) per column. Guard against zero std."""
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std = np.where(std < EPS, 1.0, std)
    return mean, std


def standardize_apply(X: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    return (X - mean) / std


# --------------------------------------------------------------- LOO cross-val
def loo_cross_validate(
    X: np.ndarray, y: np.ndarray, n_classes: int
) -> np.ndarray:
    """Leave-one-out CV. For each held-out sample, standardize using the training
    mean/std (no leakage), train, predict the held-out sample. Returns predictions."""
    n = len(y)
    preds = np.zeros(n, dtype=int)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        X_tr, y_tr = X[mask], y[mask]
        X_hold = X[i:i + 1]
        mean, std = standardize_fit(X_tr)
        X_tr_s = standardize_apply(X_tr, mean, std)
        X_hold_s = standardize_apply(X_hold, mean, std)
        W, b = train_logreg(X_tr_s, y_tr, n_classes)
        preds[i] = int(predict_logreg(X_hold_s, W, b)[0])
    return preds


# --------------------------------------------------------------- Wilson CI
def wilson_ci(correct: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Wilson score interval for a binomial proportion. Returns (p, lo, hi)."""
    if n <= 0:
        return 0.0, 0.0, 0.0
    p = correct / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return p, max(0.0, centre - margin), min(1.0, centre + margin)


# --------------------------------------------------------------- confusion matrix
def confusion_matrix(
    y_true: np.ndarray, y_pred: np.ndarray, n_classes: int
) -> np.ndarray:
    """Rows = true, cols = predicted."""
    cm = np.zeros((n_classes, n_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1
    return cm


def per_class_metrics(cm: np.ndarray) -> list[dict[str, float]]:
    """Precision, recall, F1 per class from a confusion matrix (rows=true, cols=pred)."""
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


# --------------------------------------------------------------- mode-routed detector
def mode_routed_detect(
    track: dict[str, Any], predicted_mode: str
) -> bool:
    """Mode-routed detector. Returns True if the track is flagged as hallucinated.

    Mode R -> CR detector fires (threshold 15.818, gold-calibrated).
    Diverse -> lang-id detector fires (threshold 0.409).
    Mode S -> unresolvable (never flagged).
    Non-hallucinated -> no detection.
    """
    if predicted_mode == "Mode_R":
        return track["cr"] >= GOLD_CR_THRESHOLD - EPS
    if predicted_mode == "Diverse":
        return track["lang_id_entropy"] >= LANG_ID_THRESHOLD - EPS
    # Mode_S and Non-hallucinated -> not flagged.
    return False


def bootstrap_sensitivity_ci(
    flags: np.ndarray, labels: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED
) -> tuple[float, float]:
    """Bootstrap 95% CI for sensitivity = P(flagged | hallucinated)."""
    pos_idx = np.where(labels == 1)[0]
    n_pos = len(pos_idx)
    if n_pos <= 0:
        return 0.0, 0.0
    rng = np.random.default_rng(seed)
    pos_flags = flags[pos_idx]
    sens: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n_pos, size=n_pos)
        sens.append(float(pos_flags[idx].mean()))
    return float(np.percentile(sens, 2.5)), float(np.percentile(sens, 97.5))


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gold_tracks = load_gold_tracks()
    aishell4_tracks = load_aishell4_tracks()
    all_tracks = gold_tracks + aishell4_tracks

    # --- Assign mode labels.
    for t in all_tracks:
        t["true_mode"] = assign_mode(t)

    # --- Sanity: report mode counts and the asserted Mode S windows.
    mode_counts: dict[str, int] = {m: 0 for m in MODES}
    for t in all_tracks:
        mode_counts[t["true_mode"]] += 1
    a4_mode_s_ids = [t["track_id"] for t in aishell4_tracks if t["true_mode"] == "Mode_S"]
    a4_diverse_ids = [t["track_id"] for t in aishell4_tracks if t["true_mode"] == "Diverse"]

    # --- Build feature matrix and label vector.
    feature_keys = ["cr", "lang_id_entropy", "length_ratio", "content_similarity", "num_speakers"]
    X = np.array([[t[k] for k in feature_keys] for t in all_tracks], dtype=float)
    y = np.array([MODE_TO_IDX[t["true_mode"]] for t in all_tracks], dtype=int)
    n_classes = len(MODES)

    # --- Leave-one-out cross-validation.
    y_pred = loo_cross_validate(X, y, n_classes)
    pred_modes = [MODES[p] for p in y_pred]

    # --- Accuracy + Wilson CI.
    correct = int((y_pred == y).sum())
    n_total = len(y)
    acc, acc_lo, acc_hi = wilson_ci(correct, n_total)

    # --- Majority-class baseline (always predict Non-hallucinated).
    n_nonhalluc = int((y == MODE_TO_IDX["Non-hallucinated"]).sum())
    baseline_acc = n_nonhalluc / n_total

    # --- Confusion matrix and per-class metrics.
    cm = confusion_matrix(y, y_pred, n_classes)
    class_metrics = per_class_metrics(cm)

    # --- Mode-routed detector (uses LOO predictions, no dataset prior).
    for t, pm in zip(all_tracks, pred_modes):
        t["predicted_mode"] = pm
        t["routed_flagged"] = bool(mode_routed_detect(t, pm))

    # Gold sensitivity.
    gold_halluc = [t for t in gold_tracks if t["hallucinated"]]
    gold_tp = sum(1 for t in gold_halluc if t["routed_flagged"])
    gold_sens = gold_tp / len(gold_halluc) if gold_halluc else 0.0

    # AISHELL-4 sensitivity.
    a4_halluc = [t for t in aishell4_tracks if t["hallucinated"]]
    a4_tp = sum(1 for t in a4_halluc if t["routed_flagged"])
    a4_sens = a4_tp / len(a4_halluc) if a4_halluc else 0.0

    # Bootstrap CIs for sensitivity.
    gold_flags = np.array([1 if t["routed_flagged"] else 0 for t in gold_tracks], dtype=float)
    gold_labels = np.array([1 if t["hallucinated"] else 0 for t in gold_tracks], dtype=float)
    a4_flags = np.array([1 if t["routed_flagged"] else 0 for t in aishell4_tracks], dtype=float)
    a4_labels = np.array([1 if t["hallucinated"] else 0 for t in aishell4_tracks], dtype=float)
    gold_ci = bootstrap_sensitivity_ci(gold_flags, gold_labels, seed=SEED)
    a4_ci = bootstrap_sensitivity_ci(a4_flags, a4_labels, seed=SEED + 1)

    # --- Hypothesis verdicts.
    h23a_supported = acc > 0.80
    h23a_killed = acc <= 0.70
    h23b_supported = gold_sens > 0.90 and a4_sens > 0.90
    h23b_killed = gold_sens <= 0.90 or a4_sens <= 0.90
    # Confusion matrix is diagonal iff all off-diagonal entries are zero.
    off_diag = int(cm.sum() - np.trace(cm))
    h23c_supported = off_diag > 0  # confusable modes exist
    h23c_killed = off_diag == 0    # diagonal => trivial

    # --- Feature distribution by mode (for the writeup).
    def feat_stats(mode: str) -> dict[str, dict[str, float]]:
        rows = [t for t in all_tracks if t["true_mode"] == mode]
        out: dict[str, dict[str, float]] = {}
        for k in feature_keys:
            vals = np.array([t[k] for t in rows], dtype=float)
            out[k] = {
                "n": len(vals),
                "median": round(float(np.median(vals)), 6) if len(vals) else 0.0,
                "mean": round(float(np.mean(vals)), 6) if len(vals) else 0.0,
                "min": round(float(np.min(vals)), 6) if len(vals) else 0.0,
                "max": round(float(np.max(vals)), 6) if len(vals) else 0.0,
            }
        return out

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ23: Per-track mode classifier — transcript-feature routing without a dataset prior",
        "closes_issue": 921,
        "method": (
            "reanalysis only (no Whisper / no ASR run by this script); gold features loaded "
            "from comparison_results.csv (RQ21) plus gold_track_texts.json for length_ratio "
            "and content_similarity; AISHELL-4 features computed on concatenated separated "
            "text from rq1_aishell4_validation_results.json"
        ),
        "gold_source": str(GOLD_CSV.relative_to(PROJECT_ROOT)),
        "gold_text_source": str(GOLD_TEXT_JSON.relative_to(PROJECT_ROOT)),
        "aishell4_source": str(AISHELL4_JSON.relative_to(PROJECT_ROOT)),
        "mode_definitions": {
            "Mode_R": f"hallucinated AND cr > {CR_MODE_THRESHOLD}",
            "Mode_S": f"hallucinated AND lang_id_entropy < {LANG_ID_THRESHOLD} AND cr <= {CR_MODE_THRESHOLD}",
            "Diverse": f"hallucinated AND lang_id_entropy >= {LANG_ID_THRESHOLD}",
            "Non-hallucinated": "not hallucinated",
        },
        "mode_label_note": (
            "Mode labels are derived in-sample from the same cr/lang_id_entropy features used "
            "as classifier inputs (see Limitations). This is a known circularity: the labels "
            "are deterministic functions of two of the five features."
        ),
        "feature_notes": {
            "cr": "gold: per-track (from RQ21 CSV); aishell4: concatenated separated text (per RQ23 spec)",
            "lang_id_entropy": "gold: per-track (from RQ21 CSV); aishell4: max across per-speaker texts (matching RQ21 threshold calibration)",
            "length_ratio": "gold: track_len / (sep1+sep2) proxy (no stored mixed text); aishell4: sep_total / mixed_text_len",
            "content_similarity": "gold: Jaccard(sep1, sep2) proxy; aishell4: Jaccard(sep_concat, mixed)",
            "num_speakers": "gold: 2; aishell4: per-window count",
        },
        "aggregation_note": (
            "AISHELL-4 uses a hybrid aggregation: cr on concatenated text (per the RQ23 spec; "
            "concatenation dilutes single-speaker repetition so no window exceeds the cr > 2.4 "
            "Mode R boundary) and lang_id_entropy as max across speakers (the 0.409 threshold "
            "was calibrated on max-aggregated entropy in RQ21). This reproduces the pre-registered "
            "2 Mode S / 35 Diverse split exactly. Gold uses per-track values from RQ21's CSV."
        ),
        "classifier": {
            "model": "multinomial logistic regression (softmax + L2)",
            "implementation": "numpy only (no sklearn)",
            "features": feature_keys,
            "n_features": len(feature_keys),
            "n_classes": n_classes,
            "standardization": "leave-one-out z-score (mean/std from training fold only)",
            "class_balancing": "sqrt inverse-frequency sample weights (635/42 imbalance)",
            "learning_rate": LR,
            "n_steps": N_STEPS,
            "l2": L2,
            "cv": "leave-one-out (677 folds)",
        },
        "counts": {
            "total_tracks": n_total,
            "gold_tracks": len(gold_tracks),
            "gold_hallucinated": len(gold_halluc),
            "aishell4_tracks": len(aishell4_tracks),
            "aishell4_hallucinated": len(a4_halluc),
            "mode_counts": mode_counts,
            "aishell4_mode_s_window_ids": a4_mode_s_ids,
            "aishell4_diverse_count": len(a4_diverse_ids),
        },
        "loo_accuracy": {
            "correct": correct,
            "n": n_total,
            "accuracy": round(acc, 6),
            "wilson_ci_95": [round(acc_lo, 6), round(acc_hi, 6)],
            "majority_class_baseline": round(baseline_acc, 6),
            "baseline_correct": n_nonhalluc,
            "beats_baseline": bool(acc > baseline_acc),
        },
        "confusion_matrix": {
            "row_order": MODES,
            "col_order": MODES,
            "matrix": cm.tolist(),
            "off_diagonal": off_diag,
        },
        "per_class_metrics": class_metrics,
        "mode_routed_detector": {
            "policy": "Mode R -> CR (>= 15.818); Diverse -> lang-id (>= 0.409); Mode S -> unresolvable; Non-hallucinated -> none",
            "cr_threshold": GOLD_CR_THRESHOLD,
            "lang_id_threshold": LANG_ID_THRESHOLD,
            "gold_sensitivity": round(gold_sens, 6),
            "gold_sensitivity_ci_95": [round(gold_ci[0], 6), round(gold_ci[1], 6)],
            "gold_tp": gold_tp,
            "gold_n_hallucinated": len(gold_halluc),
            "aishell4_sensitivity": round(a4_sens, 6),
            "aishell4_sensitivity_ci_95": [round(a4_ci[0], 6), round(a4_ci[1], 6)],
            "a4_tp": a4_tp,
            "a4_n_hallucinated": len(a4_halluc),
            "uses_dataset_prior": False,
        },
        "feature_distribution_by_mode": {m: feat_stats(m) for m in MODES},
        "hypothesis_verdicts": {
            "H23a": {
                "statement": "per-track mode classifier achieves > 80% accuracy (LOO) on 4-class task",
                "kill_criterion": "accuracy <= 70%",
                "accuracy": round(acc, 6),
                "wilson_ci_95": [round(acc_lo, 6), round(acc_hi, 6)],
                "majority_baseline": round(baseline_acc, 6),
                "supported": bool(h23a_supported),
                "killed": bool(h23a_killed),
            },
            "H23b": {
                "statement": "mode-routed detector achieves > 90% sensitivity on both gold and AISHELL-4 without a dataset prior",
                "kill_criterion": "sensitivity <= 90% on either dataset",
                "gold_sensitivity": round(gold_sens, 6),
                "gold_ci_95": [round(gold_ci[0], 6), round(gold_ci[1], 6)],
                "aishell4_sensitivity": round(a4_sens, 6),
                "aishell4_ci_95": [round(a4_ci[0], 6), round(a4_ci[1], 6)],
                "supported": bool(h23b_supported),
                "killed": bool(h23b_killed),
            },
            "H23c": {
                "statement": "confusion matrix reveals confusable modes",
                "kill_criterion": "confusion matrix is diagonal (no confusable modes)",
                "off_diagonal_errors": off_diag,
                "supported": bool(h23c_supported),
                "killed": bool(h23c_killed),
            },
        },
    }

    # --- Write per-track CSV.
    csv_fields = [
        "dataset", "track_id", "true_mode", "predicted_mode",
        "cr", "lang_id_entropy", "length_ratio", "content_similarity", "num_speakers",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for t in all_tracks:
            wr.writerow({
                "dataset": t["dataset"],
                "track_id": t["track_id"],
                "true_mode": t["true_mode"],
                "predicted_mode": t["predicted_mode"],
                "cr": round(t["cr"], 6),
                "lang_id_entropy": round(t["lang_id_entropy"], 6),
                "length_ratio": round(t["length_ratio"], 6),
                "content_similarity": round(t["content_similarity"], 6),
                "num_speakers": t["num_speakers"],
            })

    # --- Write JSON.
    OUT_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # --- Console summary.
    print("=== RQ23: Per-track mode classifier ===")
    print(f"Label: experimental/frontier  |  Closes #921")
    print(f"Tracks: {n_total} (gold {len(gold_tracks)} + aishell4 {len(aishell4_tracks)})")
    print(f"Mode counts: {mode_counts}")
    print(f"AISHELL-4 Mode S windows: {a4_mode_s_ids}")
    print(f"AISHELL-4 Diverse count: {len(a4_diverse_ids)}")
    print()
    print(f"LOO accuracy: {acc:.1%} ({correct}/{n_total})  Wilson CI [{acc_lo:.1%}, {acc_hi:.1%}]")
    print(f"Majority-class baseline: {baseline_acc:.1%} ({n_nonhalluc}/{n_total})")
    print(f"Beats baseline: {acc > baseline_acc}")
    print()
    print("Confusion matrix (rows=true, cols=pred):")
    print(f"{'':18s}" + "".join(f"{m[:12]:>13s}" for m in MODES))
    for i, m in enumerate(MODES):
        print(f"{m:18s}" + "".join(f"{int(cm[i, j]):13d}" for j in range(n_classes)))
    print()
    print("Per-class metrics:")
    print(f"{'class':18s} {'prec':>7s} {'rec':>7s} {'f1':>7s} {'support':>8s}")
    for c in class_metrics:
        print(f"{c['class']:18s} {c['precision']:7.1%} {c['recall']:7.1%} {c['f1']:7.1%} {c['support']:8d}")
    print()
    print("Mode-routed detector:")
    print(f"  gold:     sens={gold_sens:.1%} ({gold_tp}/{len(gold_halluc)}) CI [{gold_ci[0]:.1%}, {gold_ci[1]:.1%}]")
    print(f"  aishell4: sens={a4_sens:.1%} ({a4_tp}/{len(a4_halluc)}) CI [{a4_ci[0]:.1%}, {a4_ci[1]:.1%}]")
    print()
    print("Hypothesis verdicts:")
    print(f"  H23a (>80% acc): {'SUPPORTED' if h23a_supported else 'NOT SUPPORTED'}"
          f"{'  [KILLED]' if h23a_killed else ''}  (acc={acc:.1%})")
    print(f"  H23b (>90% sens both): {'SUPPORTED' if h23b_supported else 'NOT SUPPORTED'}"
          f"{'  [KILLED]' if h23b_killed else ''}  (gold={gold_sens:.1%}, a4={a4_sens:.1%})")
    print(f"  H23c (confusable modes): {'SUPPORTED' if h23c_supported else 'NOT SUPPORTED'}"
          f"{'  [KILLED]' if h23c_killed else ''}  (off-diag={off_diag})")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
