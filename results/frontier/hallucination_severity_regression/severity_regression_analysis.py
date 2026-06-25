"""RQ29: Hallucination severity regression — predict cpWER contribution.

REANALYSIS ONLY — no Whisper / no ASR model is run. This script reads the existing
AISHELL-4 external-validation results (``results/external_sanity_check/aishell4/
rq1_aishell4_validation_results.json``, label ``external/sanity-check``, PR #890) and
fits a leave-one-out (LOO) random-forest regressor that predicts per-window
``separated_cpwer`` and ``mixed_cpwer`` from transcript features computed from the
stored per-speaker separated transcripts and the mixed transcript.

Motivation
----------
All prior detector studies (RQ13, RQ16, RQ17, RQ19-RQ27) framed hallucination
detection as binary classification: hallucinated vs not. This (i) treats all
hallucinated tracks equally (Mode S cpWER~2.0 and Mode D cpWER~1.5 are very
different in severity), and (ii) optimises detection accuracy rather than the
downstream routing objective (cpWER). A regression subsumes detection: predict the
continuous cpWER contribution of each track, then route to mixed if predicted
``separated_cpwer`` > predicted ``mixed_cpwer``.

Method
------
For each of the 77 AISHELL-4 windows we compute 10 reference-free features:

  From the separated transcript (per-speaker texts concatenated):
    - ``cr``                 Whisper-style compression ratio (len(utf8)/len(zlib))
    - ``lang_id_entropy``    Shannon entropy (bits) over Unicode script categories
    - ``length_ratio``       separated_total_length / mixed_text_length
    - ``content_similarity`` character-bigram Jaccard(sep_concat, mixed_text)
    - ``num_speakers``       stored count
    - ``runtime_ratio``      stored separated_runtime_sec / mixed_runtime_sec
    - ``separated_total_length`` stored
    - ``mixed_text_length``  stored
  From the mixed transcript:
    - ``cr_mixed``           compression ratio of mixed_text
    - ``lang_id_entropy_mixed`` entropy of mixed_text

Targets:
    - ``separated_cpwer``    cpwer_separated.error_rate
    - ``mixed_cpwer``        orcwer_mixed.error_rate
    - ``cpwer_contribution`` separated_cpwer - mixed_cpwer  (analysis-only)

Random-forest regressor (numpy-only, no sklearn):
    - CART regression tree: recursive binary split minimising weighted child MSE;
      max_depth=8, min_samples_split=5.
    - Bootstrap aggregation: 100 trees per forest (seed=42).
    - Prediction: average across trees.
    - Two forests fit per LOO fold: one for separated_cpwer, one for mixed_cpwer.

Decision rule (regression router):
    route to MIXED if predicted_separated_cpwer > predicted_mixed_cpwer,
    else SEPARATED. Per-window cpWER = chosen route's stored cpWER.

Hypotheses (pre-registered)
---------------------------
- H29a: LOO R² > 0.5 for separated_cpwer prediction. KILL if R² ≤ 0.5.
- H29b: top-3 highest-predicted-cpWER windows include both Mode S tracks
  (window IDs 22, 30). KILL if either Mode S track is outside the top-5.
- H29c: regression-router cpWER < 1.10 on AISHELL-4. KILL if cpWER ≥ 1.10.

Comparison points (per-window-mean aggregate cpWER on the same 77 windows):
    always-mixed 1.173, always-separated 1.591, router v2 1.206,
    RQ16 corrected router 1.043, oracle best 1.017.

Label: experimental/frontier. Closes #933.
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
SRC_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "hallucination_severity_regression"
OUT_CSV = OUT_DIR / "severity_regression_results.csv"
OUT_JSON = OUT_DIR / "severity_regression_results.json"

# ----------------------------------------------------------------- hyperparams
SEED = 42
N_TREES = 100
MAX_DEPTH = 8
MIN_SAMPLES_SPLIT = 5
N_BOOT = 10000
EPS = 1e-9

# Mode S definition (RQ19, PR #915): the 2 monoscript-Chinese hallucinations that
# escape every surface detector (the RQ16 corrected-router residual).
MODE_S_WINDOW_IDS = [22, 30]

# Comparison baselines (per-window-mean cpWER on the same 77 windows; from RQ1/RQ16).
ALWAYS_MIXED_CPWER = 1.173
ALWAYS_SEPARATED_CPWER = 1.591
ROUTER_V2_CPWER = 1.206
RQ16_CORRECTED_ROUTER_CPWER = 1.043
ORACLE_BEST_CPWER = 1.017


# ----------------------------------------------------------------- text primitives
def compression_ratio(text: str) -> float:
    """Whisper-style compression ratio: len(utf8 bytes) / len(zlib-compressed bytes).

    Matches ``whisper.audio.compression_ratio`` and RQ12/RQ13/RQ16's
    ``compression_ratio``. Returns 0.0 for empty/whitespace text."""
    if not text or not text.strip():
        return 0.0
    b = text.encode("utf-8")
    c = zlib.compress(b)
    return len(b) / len(c) if len(c) > 0 else 0.0


def script_category(ch: str) -> str:
    """Map a character to a coarse Unicode script category (RQ13 verbatim)."""
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
    """Shannon entropy (bits) over the script-category distribution of the text.

    Clean Chinese (near-monoscript Han) -> entropy ~ 0. Diverse multilingual
    gibberish mixing Han+Latin+Katakana+Hangul -> high entropy. (RQ13.)"""
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


def char_ngrams(text: str, n: int) -> set[str]:
    """Set of character n-grams of length ``n`` (whitespace-collapsed)."""
    s = "".join(text.split())
    if len(s) < n:
        return {s} if s else set()
    return {s[i : i + n] for i in range(len(s) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity over two sets; 0.0 if both empty."""
    u = a | b
    if not u:
        return 0.0
    return len(a & b) / len(u)


def bigram_jaccard(sep: str, mix: str) -> float:
    """Character-bigram Jaccard similarity (RQ19 content_similarity feature)."""
    return jaccard(char_ngrams(sep, 2), char_ngrams(mix, 2))


# ---------------------------------------------------------------- feature builder
FEATURE_NAMES = [
    "cr",
    "lang_id_entropy",
    "length_ratio",
    "content_similarity",
    "num_speakers",
    "runtime_ratio",
    "separated_total_length",
    "mixed_text_length",
    "cr_mixed",
    "lang_id_entropy_mixed",
]


def compute_features(window: dict[str, Any]) -> dict[str, float]:
    """Compute the 10 reference-free features for one window.

    The separated-text features are computed on the per-speaker separated
    transcripts *concatenated* (no separator), as specified by RQ29.
    """
    sep_texts = [
        str(t)
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None
    ]
    sep_concat = "".join(sep_texts)
    mixed_text = str(window.get("mixed_text", "") or "")

    sep_len = float(window.get("separated_total_length", 0) or 0)
    mix_len = float(window.get("mixed_text_length", 0) or 0)
    length_ratio = sep_len / max(1.0, mix_len)

    return {
        "cr": compression_ratio(sep_concat),
        "lang_id_entropy": language_id_entropy(sep_concat),
        "length_ratio": length_ratio,
        "content_similarity": bigram_jaccard(sep_concat, mixed_text),
        "num_speakers": float(window.get("num_speakers", 0) or 0),
        "runtime_ratio": float(window.get("runtime_ratio", 0.0) or 0.0),
        "separated_total_length": sep_len,
        "mixed_text_length": mix_len,
        "cr_mixed": compression_ratio(mixed_text),
        "lang_id_entropy_mixed": language_id_entropy(mixed_text),
    }


# --------------------------------------------------------- CART regression tree
class _CARTRegressionTree:
    """CART regression tree: recursive binary split minimising weighted child MSE.

    Stopping: max_depth, min_samples_split, or node purity (variance ~ 0).
    Leaf value = mean of y in the leaf.
    """

    def __init__(self, max_depth: int = MAX_DEPTH, min_samples_split: int = MIN_SAMPLES_SPLIT):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.root: dict[str, Any] | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "_CARTRegressionTree":
        self.root = self._build(X, y, depth=0)
        return self

    def _build(self, X: np.ndarray, y: np.ndarray, depth: int) -> dict[str, Any]:
        n = len(y)
        # Leaf conditions: depth limit, too few samples to split, or pure node.
        if depth >= self.max_depth or n < self.min_samples_split or n == 0:
            return {"leaf": True, "value": float(y.mean()) if n > 0 else 0.0}

        # Pre-compute parent SSE for gain computation (used only for the best-split
        # search; we actually select splits by min weighted child SSE, which is
        # equivalent to max variance reduction for a fixed parent).
        parent_var = float(y.var()) if n > 0 else 0.0
        if parent_var <= EPS:
            return {"leaf": True, "value": float(y.mean())}

        best = self._best_split(X, y)
        if best is None:
            return {"leaf": True, "value": float(y.mean())}

        feat_idx, thr, left_idx, right_idx = best
        # Guard against degenerate splits (one side empty).
        if len(left_idx) == 0 or len(right_idx) == 0:
            return {"leaf": True, "value": float(y.mean())}

        return {
            "leaf": False,
            "feat_idx": feat_idx,
            "thr": thr,
            "left": self._build(X[left_idx], y[left_idx], depth + 1),
            "right": self._build(X[right_idx], y[right_idx], depth + 1),
        }

    def _best_split(
        self, X: np.ndarray, y: np.ndarray
    ) -> tuple[int, float, np.ndarray, np.ndarray] | None:
        """Find the (feature, threshold) split minimising weighted child SSE.

        For efficiency we evaluate candidate thresholds at the midpoints between
        consecutive sorted unique values per feature (CART convention). Returns
        None if no split reduces SSE below the parent SSE.
        """
        n, d = X.shape
        parent_sse = float(((y - y.mean()) ** 2).sum())
        best_sse = parent_sse
        best: tuple[int, float, np.ndarray, np.ndarray] | None = None

        for j in range(d):
            col = X[:, j]
            order = np.argsort(col, kind="mergesort")
            col_sorted = col[order]
            y_sorted = y[order]
            # Prefix sums for O(n) SSE computation per feature.
            n_left = np.arange(1, n)  # candidate split sizes 1..n-1
            sum_left = np.cumsum(y_sorted)[:-1]
            sumsq_left = np.cumsum(y_sorted * y_sorted)[:-1]
            sum_total = sum_left[-1] + y_sorted[-1]
            sumsq_total = sumsq_left[-1] + y_sorted[-1] * y_sorted[-1]
            sum_right = sum_total - sum_left
            sumsq_right = sumsq_total - sumsq_left
            n_right = n - n_left

            # SSE_left = sumsq_left - sum_left^2 / n_left (guard div-by-zero).
            with np.errstate(divide="ignore", invalid="ignore"):
                sse_left = sumsq_left - (sum_left * sum_left) / n_left
                sse_right = sumsq_right - (sum_right * sum_right) / n_right
            sse = sse_left + sse_right
            # Replace NaNs (shouldn't happen but guard) with +inf.
            sse = np.where(np.isfinite(sse), sse, np.inf)

            # Only consider splits where the threshold strictly separates values
            # (i.e., col_sorted[k] != col_sorted[k+1]).
            valid = col_sorted[:-1] < col_sorted[1:]
            sse = np.where(valid, sse, np.inf)

            if not np.any(np.isfinite(sse)):
                continue

            k = int(np.argmin(sse))
            if sse[k] < best_sse - EPS:
                best_sse = float(sse[k])
                thr = float((col_sorted[k] + col_sorted[k + 1]) / 2.0)
                # Map back to original indices.
                left_mask = col <= thr
                right_mask = ~left_mask
                left_idx = np.where(left_mask)[0]
                right_idx = np.where(right_mask)[0]
                best = (j, thr, left_idx, right_idx)

        return best

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.root is None:
            raise RuntimeError("tree not fit")
        out = np.empty(len(X), dtype=float)
        for i in range(len(X)):
            node = self.root
            while not node["leaf"]:
                if X[i, node["feat_idx"]] <= node["thr"]:
                    node = node["left"]
                else:
                    node = node["right"]
            out[i] = node["value"]
        return out


# ----------------------------------------------------- random forest regressor
class RandomForestRegressor:
    """Bootstrap-aggregated CART regression trees (numpy-only).

    ``n_trees`` bootstrap samples of size ``n`` (with replacement); each tree is
    a fully-grown CART tree (subject to max_depth / min_samples_split). Prediction
    = mean across trees. ``max_features`` defaults to all features (no random
    feature subsampling); set < d for a feature-subsampled forest.
    """

    def __init__(
        self,
        n_trees: int = N_TREES,
        max_depth: int = MAX_DEPTH,
        min_samples_split: int = MIN_SAMPLES_SPLIT,
        max_features: int | None = None,
        seed: int = SEED,
    ):
        self.n_trees = n_trees
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.max_features = max_features
        self.rng = np.random.default_rng(seed)
        self.trees: list[_CARTRegressionTree] = []
        self.feature_subsets: list[np.ndarray] = []

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RandomForestRegressor":
        n, d = X.shape
        self.trees = []
        self.feature_subsets = []
        for _ in range(self.n_trees):
            idx = self.rng.integers(0, n, size=n)  # bootstrap sample
            if self.max_features is None or self.max_features >= d:
                feat_idx = np.arange(d)
            else:
                feat_idx = self.rng.choice(d, size=self.max_features, replace=False)
                feat_idx.sort()
            tree = _CARTRegressionTree(
                max_depth=self.max_depth, min_samples_split=self.min_samples_split
            )
            tree.fit(X[idx][:, feat_idx], y[idx])
            self.trees.append(tree)
            self.feature_subsets.append(feat_idx)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        preds = np.empty((len(self.trees), len(X)), dtype=float)
        for i, (tree, feat_idx) in enumerate(zip(self.trees, self.feature_subsets)):
            preds[i] = tree.predict(X[:, feat_idx])
        return preds.mean(axis=0)


# ----------------------------------------------------------------- LOO CV
def loo_cv_predict(
    X: np.ndarray, y: np.ndarray, seed: int = SEED
) -> np.ndarray:
    """Leave-one-out CV predictions for a RandomForestRegressor.

    For each held-out sample i, fit a fresh RF on the other n-1 samples with a
    derived seed (so each fold is reproducible but distinct) and predict y[i].
    """
    n = len(y)
    preds = np.empty(n, dtype=float)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        X_tr = X[mask]
        y_tr = y[mask]
        # Per-fold seed = base + fold index, so each fold is deterministic and
        # distinct yet reproducible across runs.
        rf = RandomForestRegressor(seed=seed + i)
        rf.fit(X_tr, y_tr)
        preds[i] = float(rf.predict(X[i : i + 1])[0])
    return preds


# ----------------------------------------------------------------- metrics
def r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = float(((y_true - y_pred) ** 2).sum())
    ss_tot = float(((y_true - y_true.mean()) ** 2).sum())
    if ss_tot <= EPS:
        return 0.0
    return 1.0 - ss_res / ss_tot


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.abs(y_true - y_pred).mean())


def spearman_rho(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman rank correlation (no scipy dependency; ties averaged)."""
    ra = _rank(a)
    rb = _rank(b)
    return float(_pearson(ra, rb))


def _rank(x: np.ndarray) -> np.ndarray:
    """Average-rank of each element (ties share the mean rank)."""
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype=float)
    sx = x[order]
    i = 0
    n = len(x)
    while i < n:
        j = i
        while j + 1 < n and sx[j + 1] == sx[i]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # ranks are 1-indexed
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    am = a - a.mean()
    bm = b - b.mean()
    denom = math.sqrt(float((am * am).sum()) * float((bm * bm).sum()))
    if denom <= EPS:
        return 0.0
    return float((am * bm).sum() / denom)


def bootstrap_mean_ci(values: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(values)
    means = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        means[i] = float(values[idx].mean())
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def bootstrap_diff_ci(
    a: np.ndarray, b: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(a)
    diffs = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        diffs[i] = float(a[idx].mean() - b[idx].mean())
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


# ----------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]
    n = len(windows)
    assert n == 77, f"expected 77 windows, got {n}"

    # ---- feature matrix + targets
    feat_rows = [compute_features(w) for w in windows]
    X = np.array([[r[k] for k in FEATURE_NAMES] for r in feat_rows], dtype=float)
    y_sep = np.array([float(w["cpwer_separated"]["error_rate"]) for w in windows], dtype=float)
    y_mix = np.array([float(w["orcwer_mixed"]["error_rate"]) for w in windows], dtype=float)
    y_contrib = y_sep - y_mix
    window_ids = np.array([w["window_id"] for w in windows], dtype=int)

    # Sanity: feature matrix is finite.
    assert np.all(np.isfinite(X)), "non-finite feature value detected"
    assert np.all(np.isfinite(y_sep)) and np.all(np.isfinite(y_mix))

    # ---- LOO predictions
    sep_pred = loo_cv_predict(X, y_sep, seed=SEED)
    mix_pred = loo_cv_predict(X, y_mix, seed=SEED + 1000)

    # ---- metrics on separated_cpwer prediction (H29a)
    loo_r2 = r2_score(y_sep, sep_pred)
    loo_mae = mae(y_sep, sep_pred)
    rho = spearman_rho(y_sep, sep_pred)

    # Metrics on mixed_cpwer prediction (secondary)
    loo_r2_mixed = r2_score(y_mix, mix_pred)
    loo_mae_mixed = mae(y_mix, mix_pred)
    rho_mixed = spearman_rho(y_mix, mix_pred)

    # ---- H29b: top-3 highest-predicted separated_cpwer windows
    pred_order = np.argsort(-sep_pred, kind="mergesort")  # descending
    top3_predicted = [int(window_ids[i]) for i in pred_order[:3]]
    top5_predicted = [int(window_ids[i]) for i in pred_order[:5]]
    top10_predicted = [int(window_ids[i]) for i in pred_order[:10]]

    # Rank of each Mode S window by predicted cpwer (1-indexed).
    rank_by_pred = {int(window_ids[pred_order[k]]): k + 1 for k in range(n)}
    mode_s_ranks = {wid: rank_by_pred.get(wid, -1) for wid in MODE_S_WINDOW_IDS}

    # Also report rank by ACTUAL cpwer (to expose the data-level ceiling).
    actual_order = np.argsort(-y_sep, kind="mergesort")
    rank_by_actual = {int(window_ids[actual_order[k]]): k + 1 for k in range(n)}
    mode_s_actual_ranks = {wid: rank_by_actual.get(wid, -1) for wid in MODE_S_WINDOW_IDS}

    h29b_top3_includes_both = all(wid in top3_predicted for wid in MODE_S_WINDOW_IDS)
    h29b_top5_includes_both = all(wid in top5_predicted for wid in MODE_S_WINDOW_IDS)

    # ---- H29c: regression router
    # Route to MIXED if predicted_sep > predicted_mix, else SEPARATED.
    # Per-window cpWER = chosen route's stored cpwer.
    router_decisions: list[str] = []
    router_cpwers: list[float] = []
    oracle_decisions: list[str] = []
    oracle_cpwers: list[float] = []
    for i, w in enumerate(windows):
        # Regression router
        if sep_pred[i] > mix_pred[i]:
            dec = "mixed"
            cp = float(w["always_mixed_cpwer"])
        else:
            dec = "separated"
            cp = float(w["always_separated_cpwer"])
        router_decisions.append(dec)
        router_cpwers.append(cp)
        # Oracle router (for reference)
        if w["always_mixed_cpwer"] <= w["always_separated_cpwer"]:
            oracle_decisions.append("mixed")
            oracle_cpwers.append(float(w["always_mixed_cpwer"]))
        else:
            oracle_decisions.append("separated")
            oracle_cpwers.append(float(w["always_separated_cpwer"]))

    router_cpwer = float(np.mean(router_cpwers))
    oracle_cpwer = float(np.mean(oracle_cpwers))
    always_mixed = float(np.mean([float(w["always_mixed_cpwer"]) for w in windows]))
    always_separated = float(np.mean([float(w["always_separated_cpwer"]) for w in windows]))
    router_v2 = float(np.mean([float(w["router_v2_cpwer"]) for w in windows]))

    # Decision mix
    router_counts = {"mixed": router_decisions.count("mixed"), "separated": router_decisions.count("separated")}
    oracle_counts = {"mixed": oracle_decisions.count("mixed"), "separated": oracle_decisions.count("separated")}

    # Bootstrap CIs for the router (paired per-window resample).
    router_arr = np.array(router_cpwers, dtype=float)
    mixed_arr = np.array([float(w["always_mixed_cpwer"]) for w in windows], dtype=float)
    sep_arr = np.array([float(w["always_separated_cpwer"]) for w in windows], dtype=float)
    rv2_arr = np.array([float(w["router_v2_cpwer"]) for w in windows], dtype=float)
    oracle_arr = np.array(oracle_cpwers, dtype=float)
    ci_router_vs_mixed = bootstrap_diff_ci(router_arr, mixed_arr)
    ci_router_vs_rv2 = bootstrap_diff_ci(router_arr, rv2_arr)
    ci_router_vs_oracle = bootstrap_diff_ci(router_arr, oracle_arr)
    ci_router_lo, ci_router_hi = bootstrap_mean_ci(router_arr)

    # ---- Hypothesis verdicts
    h29a_supported = bool(loo_r2 > 0.5)
    h29b_supported = bool(h29b_top3_includes_both and h29b_top5_includes_both)
    h29c_supported = bool(router_cpwer < 1.10)

    # ---- per-window CSV
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        wcsv = csv.writer(f)
        wcsv.writerow([
            "window_id",
            "actual_separated_cpwer",
            "predicted_separated_cpwer",
            "actual_mixed_cpwer",
            "predicted_mixed_cpwer",
            "cpwer_contribution",
            "regression_router_decision",
            "regression_router_cpwer",
            "oracle_decision",
            "oracle_cpwer",
            "is_mode_s",
            *FEATURE_NAMES,
        ])
        for i, ww in enumerate(windows):
            wcsv.writerow([
                int(window_ids[i]),
                round(float(y_sep[i]), 6),
                round(float(sep_pred[i]), 6),
                round(float(y_mix[i]), 6),
                round(float(mix_pred[i]), 6),
                round(float(y_contrib[i]), 6),
                router_decisions[i],
                round(float(router_cpwers[i]), 6),
                oracle_decisions[i],
                round(float(oracle_cpwers[i]), 6),
                int(int(window_ids[i]) in MODE_S_WINDOW_IDS),
                *[round(float(X[i, j]), 6) for j in range(len(FEATURE_NAMES))],
            ])

    # ---- JSON results
    results: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ29: hallucination severity regression — predict per-track cpWER contribution instead of binary detection",
        "closes_issue": 933,
        "method": (
            "reanalysis only (no Whisper / no ASR run); per-window reference-free "
            "transcript features fit to a leave-one-out random-forest regressor "
            "(numpy-only CART + bootstrap aggregation, 100 trees, max_depth=8, "
            "min_samples_split=5, seed=42) predicting separated_cpwer and "
            "mixed_cpwer. Regression router routes to MIXED if predicted "
            "separated_cpwer > predicted mixed_cpwer, else SEPARATED. Aggregate "
            "cpWER is the per-window mean of the chosen route's stored cpwer "
            "(same metric as RQ1/RQ16)."
        ),
        "source_data": "results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json",
        "source_label": "external/sanity-check",
        "meeting_id": data.get("meeting_id"),
        "n_windows": n,
        "features": FEATURE_NAMES,
        "feature_descriptions": {
            "cr": "Whisper-style compression ratio of separated-text concatenated across speakers (len(utf8)/len(zlib))",
            "lang_id_entropy": "Shannon entropy (bits) over Unicode script categories of the concatenated separated text",
            "length_ratio": "separated_total_length / max(1, mixed_text_length)",
            "content_similarity": "character-bigram Jaccard(separated_concat, mixed_text)",
            "num_speakers": "stored num_speakers",
            "runtime_ratio": "stored separated_runtime_sec / mixed_runtime_sec",
            "separated_total_length": "stored separated_total_length",
            "mixed_text_length": "stored mixed_text_length",
            "cr_mixed": "compression ratio of mixed_text",
            "lang_id_entropy_mixed": "Shannon entropy of mixed_text",
        },
        "targets": {
            "separated_cpwer": "cpwer_separated.error_rate",
            "mixed_cpwer": "orcwer_mixed.error_rate",
            "cpwer_contribution": "separated_cpwer - mixed_cpwer (analysis-only)",
        },
        "model": {
            "type": "RandomForestRegressor (numpy-only, no sklearn)",
            "n_trees": N_TREES,
            "max_depth": MAX_DEPTH,
            "min_samples_split": MIN_SAMPLES_SPLIT,
            "max_features": "all (no feature subsampling)",
            "bootstrap": "sample-with-replacement, size n",
            "leaf_value": "mean of y in leaf",
            "split_criterion": "minimise weighted child SSE (equivalent to max variance reduction)",
            "cv": "leave-one-out (77 folds; per-fold RF fit on 76 samples, seed = 42 + fold_index)",
            "seed": SEED,
        },
        "hypotheses": {
            "H29a": {
                "statement": "LOO R² > 0.5 on AISHELL-4 for separated_cpwer prediction",
                "kill_condition": "R² ≤ 0.5",
                "loo_r2": round(loo_r2, 6),
                "verdict": "SUPPORTED" if h29a_supported else "NOT SUPPORTED",
            },
            "H29b": {
                "statement": "top-3 highest-predicted-cpWER windows include both Mode S tracks (window IDs 22, 30)",
                "kill_condition": "either Mode S track outside the top-5",
                "top3_predicted_windows": top3_predicted,
                "top5_predicted_windows": top5_predicted,
                "mode_s_predicted_ranks": mode_s_ranks,
                "mode_s_actual_ranks_by_separated_cpwer": mode_s_actual_ranks,
                "both_in_top3": bool(h29b_top3_includes_both),
                "both_in_top5": bool(h29b_top5_includes_both),
                "verdict": "SUPPORTED" if h29b_supported else "NOT SUPPORTED",
            },
            "H29c": {
                "statement": "regression-based router cpWER < 1.10 on AISHELL-4",
                "kill_condition": "cpWER ≥ 1.10",
                "regression_router_cpwer": round(router_cpwer, 6),
                "bootstrap_ci_95_router_cpwer": [round(ci_router_lo, 6), round(ci_router_hi, 6)],
                "verdict": "SUPPORTED" if h29c_supported else "NOT SUPPORTED",
            },
        },
        "loo_metrics": {
            "separated_cpwer": {
                "r2": round(loo_r2, 6),
                "mae": round(loo_mae, 6),
                "spearman_rho": round(rho, 6),
            },
            "mixed_cpwer": {
                "r2": round(loo_r2_mixed, 6),
                "mae": round(loo_mae_mixed, 6),
                "spearman_rho": round(rho_mixed, 6),
            },
        },
        "regression_router": {
            "cpwer": round(router_cpwer, 6),
            "bootstrap_ci_95": [round(ci_router_lo, 6), round(ci_router_hi, 6)],
            "decision_counts": router_counts,
            "ci_router_minus_mixed": [round(ci_router_vs_mixed[0], 6), round(ci_router_vs_mixed[1], 6)],
            "ci_router_minus_router_v2": [round(ci_router_vs_rv2[0], 6), round(ci_router_vs_rv2[1], 6)],
            "ci_router_minus_oracle": [round(ci_router_vs_oracle[0], 6), round(ci_router_vs_oracle[1], 6)],
        },
        "comparison_to_rq16": {
            "always_mixed_cpwer": round(always_mixed, 6),
            "always_separated_cpwer": round(always_separated, 6),
            "router_v2_cpwer": round(router_v2, 6),
            "rq16_corrected_router_cpwer": RQ16_CORRECTED_ROUTER_CPWER,
            "regression_router_cpwer": round(router_cpwer, 6),
            "oracle_best_cpwer": round(oracle_cpwer, 6),
            "regression_router_vs_corrected_router": round(router_cpwer - RQ16_CORRECTED_ROUTER_CPWER, 6),
            "regression_router_vs_oracle": round(router_cpwer - oracle_cpwer, 6),
        },
        "top3_predicted_windows": top3_predicted,
        "top5_predicted_windows": top5_predicted,
        "top10_predicted_windows": top10_predicted,
        "mode_s_window_ids": MODE_S_WINDOW_IDS,
        "mode_s_predicted_ranks": mode_s_ranks,
        "mode_s_actual_ranks_by_separated_cpwer": mode_s_actual_ranks,
        "mode_s_note": (
            "Mode S windows (22, 30) are the 2 monoscript-Chinese hallucinations "
            "that escape every RQ16 surface detector (RQ19). However their actual "
            "separated_cpwer is 2.0, which is far from the highest in the "
            "distribution (windows 73=4.333, 26=3.5, 45=3.25, 11=3.0, ... all "
            "exceed them). H29b's premise that Mode S windows are the "
            "highest-cpWER tracks is therefore not supported by the data."
        ),
        "oracle_router": {
            "cpwer": round(oracle_cpwer, 6),
            "decision_counts": oracle_counts,
        },
        "per_window": [
            {
                "window_id": int(window_ids[i]),
                "actual_separated_cpwer": round(float(y_sep[i]), 6),
                "predicted_separated_cpwer": round(float(sep_pred[i]), 6),
                "actual_mixed_cpwer": round(float(y_mix[i]), 6),
                "predicted_mixed_cpwer": round(float(mix_pred[i]), 6),
                "cpwer_contribution": round(float(y_contrib[i]), 6),
                "regression_router_decision": router_decisions[i],
                "regression_router_cpwer": round(float(router_cpwers[i]), 6),
                "oracle_decision": oracle_decisions[i],
                "oracle_cpwer": round(float(oracle_cpwers[i]), 6),
                "is_mode_s": int(int(window_ids[i]) in MODE_S_WINDOW_IDS),
            }
            for i in range(n)
        ],
        "references": {
            "rq1_aishell4_validation": "results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json (label external/sanity-check, PR #890)",
            "rq12_router_failure_modes": "results/frontier/router_failure_modes/ (RQ12 hallucination modes)",
            "rq13_diverse_hallucination_detector": "results/frontier/diverse_hallucination_detector/ (lang_id_entropy detector, threshold 0.409)",
            "rq16_corrected_router": "results/frontier/corrected_router_simulation/ (cpWER 1.043 baseline)",
            "rq19_mode_s_detector": "results/frontier/mode_s_detector/ (Mode S definition; window IDs 22, 30)",
        },
    }
    OUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- console summary
    print("=" * 78)
    print("RQ29: hallucination severity regression — predict cpWER contribution")
    print("=" * 78)
    print(f"n_windows = {n}   features = {len(FEATURE_NAMES)}   trees = {N_TREES}")
    print()
    print("LOO metrics (separated_cpwer prediction):")
    print(f"  R²         = {loo_r2:.4f}")
    print(f"  MAE        = {loo_mae:.4f}")
    print(f"  Spearman ρ = {rho:.4f}")
    print()
    print("LOO metrics (mixed_cpwer prediction):")
    print(f"  R²         = {loo_r2_mixed:.4f}")
    print(f"  MAE        = {loo_mae_mixed:.4f}")
    print(f"  Spearman ρ = {rho_mixed:.4f}")
    print()
    print("Top-3 highest-predicted separated_cpwer windows:", top3_predicted)
    print("Top-5 highest-predicted separated_cpwer windows:", top5_predicted)
    print(f"Mode S window predicted ranks: {mode_s_ranks}")
    print(f"Mode S window actual ranks (by separated_cpwer): {mode_s_actual_ranks}")
    print()
    print("Regression router:")
    print(f"  cpWER = {router_cpwer:.4f}  (95% CI [{ci_router_lo:.4f}, {ci_router_hi:.4f}])")
    print(f"  decisions: {router_counts}")
    print()
    print("Comparison (per-window-mean cpWER):")
    print(f"  always-mixed            = {always_mixed:.4f}")
    print(f"  always-separated        = {always_separated:.4f}")
    print(f"  router v2               = {router_v2:.4f}")
    print(f"  RQ16 corrected router   = {RQ16_CORRECTED_ROUTER_CPWER:.4f}")
    print(f"  regression router (RQ29)= {router_cpwer:.4f}")
    print(f"  oracle best             = {oracle_cpwer:.4f}")
    print()
    print("Hypothesis verdicts:")
    print(f"  H29a (LOO R² > 0.5):                  {'SUPPORTED' if h29a_supported else 'NOT SUPPORTED'}  (R² = {loo_r2:.4f})")
    print(f"  H29b (Mode S both in top-3):          {'SUPPORTED' if h29b_supported else 'NOT SUPPORTED'}  (top-3 = {top3_predicted})")
    print(f"  H29c (regression router cpWER < 1.10):{'SUPPORTED' if h29c_supported else 'NOT SUPPORTED'}  (cpWER = {router_cpwer:.4f})")
    print()
    print(f"CSV  -> {OUT_CSV}")
    print(f"JSON -> {OUT_JSON}")


if __name__ == "__main__":
    main()
