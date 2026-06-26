"""RQ47: Tied-cpWER window characterisation on AISHELL-4.

REANALYSIS ONLY — no Whisper / no ASR / no MeetEval / no scipy / no sklearn.
This script reads the existing AISHELL-4 external-validation results
(``results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json``,
label ``external/sanity-check``, PR #890; 77 windows) and characterises the
"tied" windows — windows where ``always_mixed_cpwer == always_separated_cpwer``
(within 1e-6), so the corrected router cannot improve over always-mixed no
matter which route it picks.

RQ39 (PR #960) showed the corrected router's word-level BCa CI [1.0130, 1.0974]
*includes* the oracle (1.0173): the corrected router reaches the oracle within
statistical noise (H39b NOT SUPPORTED). RQ47 asks what properties the tied
windows share, and whether they form a separable class that could be excluded
from routing decisions.

Hypotheses (pre-registered)
---------------------------
- H47a: Tied windows have fewer active speakers than non-tied windows
  (Mann-Whitney U, two-sided p < 0.05). Kill: p >= 0.05.
- H47b: Tied windows have lower overlap ratio than non-tied windows
  (Mann-Whitney U, two-sided p < 0.05). Kill: p >= 0.05.
- H47c: A metadata-only logistic regression (numpy-only, LOO-CV) can identify
  tied windows with AUC > 0.70. Kill: AUC <= 0.70.

Method
------
1. Load the 77 AISHELL-4 windows (read-only).
2. Mark a window "tied" iff ``abs(always_mixed_cpwer - always_separated_cpwer)
   < 1e-6`` (the corrected router is constrained to {mixed, separated}, so on a
   tie both routes give the same cpWER and no routing decision can help).
3. Extract per-window metadata features: speaker count, active speaker count
   (speakers with non-empty separated hypothesis — the deployable diarisation
   proxy), overlap ratio, mixed transcript length, separated transcript length,
   total separated chars, runtime ratio, average per-speaker separated length,
   language-id entropy (Shannon entropy over Unicode script categories, max
   across per-speaker separated tracks — lifted verbatim from RQ13/RQ16), and
   compression ratio (separated / mixed length, the RQ16 ``length_ratio``).
4. Compare tied vs non-tied feature distributions with a from-scratch
   Mann-Whitney U (normal approximation, tie-corrected, continuity-corrected)
   and report the rank-biserial effect size.
5. Fit a from-scratch L2-regularised logistic regression (numpy-only, gradient
   descent, seed=42) with leave-one-out CV; report out-of-fold AUC.
6. Qualitatively characterise the tied windows (silence / short / single-speaker).

Implementation note on the tie count
------------------------------------
The task brief's narrative mentions "5 tied windows", but the stated operational
definition (``always_mixed_cpwer == always_separated_cpwer`` within 1e-6) yields
**35** tied windows on the 77-window AISHELL-4 file (34 of which tie at exactly
1.0). No natural alternative definition (mixed==sep==1.0, router==mixed==sep,
router misses oracle, etc.) yields 5. We implement the precise operational
definition — 35 tied windows — and surface the discrepancy in FINDINGS.md / the
PR body. With only 5 positives a Mann-Whitney test and a logistic-regression
AUC would be near-uninformative; the 35/42 split is the analytically meaningful
one and matches the pre-registered hypotheses.

Label: experimental/frontier. Closes the RQ47 issue.

Run:
    /opt/homebrew/bin/python3 results/frontier/tied_cpwer_characterisation/tied_cpwer_analysis.py
"""
from __future__ import annotations

import csv
import json
import math
import unicodedata
from pathlib import Path
from typing import Any, Sequence

import numpy as np

# --------------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_DIR = Path(__file__).resolve().parent
CSV_PATH = OUT_DIR / "tied_cpwer_results.csv"
JSON_PATH = OUT_DIR / "tied_cpwer_results.json"

TIE_TOL = 1e-6
SEED = 42
LABEL = "experimental/frontier"

# Features used by the metadata-only classifier (H47c). All are available
# before the cpWER that defines the label is computed (i.e. no label leakage
# from the cpWER values themselves): speaker count and overlap ratio come from
# diarisation; transcript lengths, lang-id entropy and compression ratio come
# from the ASR hypotheses; runtime ratio comes from the two ASR passes.
CLASSIFIER_FEATURES = [
    "speaker_count",
    "active_speaker_count",
    "overlap_ratio",
    "mixed_text_length",
    "separated_text_length",
    "runtime_ratio",
    "avg_speaker_length_sep",
    "lang_id_entropy",
    "compression_ratio",
]

# Every feature for which we run a Mann-Whitney comparison (broader than the
# classifier set: includes total_separated_chars and active_speaker_count_ref
# for transparency).
MWU_FEATURES = [
    "speaker_count",
    "active_speaker_count",
    "active_speaker_count_ref",
    "overlap_ratio",
    "mixed_text_length",
    "separated_text_length",
    "total_separated_chars",
    "runtime_ratio",
    "avg_speaker_length_sep",
    "lang_id_entropy",
    "compression_ratio",
]


# ----------------------------------------------------------------- lang-id (RQ13)
def script_category(ch: str) -> str:
    """Map a character to a coarse Unicode script category (RQ13 verbatim).

    Whitespace -> "Space"; punctuation/symbols -> "Punct"; control/unknown ->
    "Other". Sufficient to separate Han / Latin / Hiragana / Katakana / Hangul
    / Cyrillic / Arabic / Greek / Digit.
    """
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
    """Shannon entropy (bits) over the script-category distribution (RQ13).

    Clean monoscript Chinese -> ~0 bits; diverse multilingual gibberish
    (Han+Latin+Katakana+Hangul) -> high entropy. Empty/whitespace -> 0.0.
    """
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


def max_across_speakers(speaker_texts: dict[str, str]) -> float:
    """Max of language_id_entropy over per-speaker separated transcripts.

    A window is flagged if ANY speaker track trips the detector (worst-case
    track, RQ12/RQ13 convention). Empty/whitespace speaker texts are skipped.
    """
    vals = [
        language_id_entropy(str(t))
        for t in speaker_texts.values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


# --------------------------------------------------------------- tie identification
def identify_tied_windows(windows: Sequence[dict[str, Any]], tol: float = TIE_TOL) -> list[int]:
    """Return the ``window_id``s of tied windows.

    A window is tied iff ``abs(always_mixed_cpwer - always_separated_cpwer) <
    tol``: both routes give the same cpWER, so the corrected router (constrained
    to {mixed, separated}) cannot improve over always-mixed on that window.
    """
    tied_ids: list[int] = []
    for w in windows:
        mixed = float(w["always_mixed_cpwer"])
        sep = float(w["always_separated_cpwer"])
        if abs(mixed - sep) < tol:
            tied_ids.append(int(w["window_id"]))
    return tied_ids


def extract_window_features(window: dict[str, Any]) -> dict[str, Any]:
    """Extract the metadata features for one window (pure, no I/O).

    ``active_speaker_count`` counts speakers with non-empty separated
    hypothesis (the deployable diarisation/separator proxy); the ``_ref``
    variant counts speakers with non-empty reference text (ground-truth
    speakers who spoke) and is reported for cross-checking only.
    ``compression_ratio`` is the RQ16 ``length_ratio`` (separated / mixed
    length, mixed floored at 1). ``avg_speaker_length_sep`` is the mean
    separated hypothesis length over active (non-empty) speakers (0 if none).
    """
    sep_texts = window.get("separated_text_per_speaker", {}) or {}
    ref_texts = window.get("ref_text_per_speaker", {}) or {}
    sep_total = int(window.get("separated_total_length", 0) or 0)
    mixed_len = int(window.get("mixed_text_length", 0) or 0)

    active_sep = sum(1 for t in sep_texts.values() if t is not None and str(t).strip())
    active_ref = sum(1 for t in ref_texts.values() if t is not None and str(t).strip())
    total_separated_chars = sum(len(str(t)) for t in sep_texts.values())

    avg_speaker_length_sep = sep_total / active_sep if active_sep > 0 else 0.0
    compression_ratio = sep_total / max(1, mixed_len)
    lang_ent = max_across_speakers(sep_texts)

    return {
        "window_id": int(window["window_id"]),
        "speaker_count": int(window.get("num_speakers", 0) or 0),
        "active_speaker_count": active_sep,
        "active_speaker_count_ref": active_ref,
        "overlap_ratio": float(window.get("overlap_ratio", 0.0) or 0.0),
        "overlap_level": int(window.get("overlap_level", 0) or 0),
        "overlap_label": str(window.get("overlap_label", "")),
        "mixed_text_length": mixed_len,
        "separated_text_length": sep_total,
        "total_separated_chars": int(total_separated_chars),
        "runtime_ratio": float(window.get("runtime_ratio", 0.0) or 0.0),
        "avg_speaker_length_sep": float(avg_speaker_length_sep),
        "lang_id_entropy": float(lang_ent),
        "compression_ratio": float(compression_ratio),
        "always_mixed_cpwer": float(window.get("always_mixed_cpwer", 0.0)),
        "always_separated_cpwer": float(window.get("always_separated_cpwer", 0.0)),
        "oracle_best_cpwer": float(window.get("oracle_best_cpwer", 0.0)),
        "router_v2_method": str(window.get("router_v2_method", "")),
    }


# ----------------------------------------------------------------- ranking helpers
def rankdata_average(a: Sequence[float]) -> np.ndarray:
    """Average-rank (mid-rank) of values, 1-based. Ties share their mean rank.

    Pure numpy/stdlib implementation matching ``scipy.stats.rankdata(method='average')``.
    """
    arr = np.asarray(a, dtype=float)
    n = arr.shape[0]
    if n == 0:
        return np.zeros(0, dtype=float)
    order = np.argsort(arr, kind="mergesort")
    ranks = np.empty(n, dtype=float)
    i = 0
    while i < n:
        j = i + 1
        while j < n and arr[order[j]] == arr[order[i]]:
            j += 1
        # ranks order[i..j-1] all get the average of (i+1 .. j)
        avg_rank = (i + 1 + j) / 2.0
        ranks[order[i:j]] = avg_rank
        i = j
    return ranks


def _normal_cdf(z: float) -> float:
    """Standard normal CDF via ``math.erf`` (no scipy)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def mann_whitney_u(
    x: Sequence[float], y: Sequence[float]
) -> dict[str, float]:
    """Mann-Whitney U test (two-sided) with tie correction + continuity
    correction, plus the rank-biserial effect size. Numpy + stdlib only.

    Returns ``U`` (U for x, count-based via ranks), ``z`` (continuity-corrected
    normal-approximation z), ``p_two_sided``, ``rank_biserial`` (positive when x
    tends larger; r = 2*U/(n1*n2) - 1), and the sample sizes.
    """
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    n1 = xa.shape[0]
    n2 = ya.shape[0]
    if n1 == 0 or n2 == 0:
        return {
            "U": float("nan"),
            "z": float("nan"),
            "p_two_sided": float("nan"),
            "rank_biserial": float("nan"),
            "n1": n1,
            "n2": n2,
        }
    combined = np.concatenate([xa, ya])
    ranks = rankdata_average(combined)
    r1 = float(ranks[:n1].sum())

    u1 = r1 - n1 * (n1 + 1) / 2.0  # U for x
    u2 = n1 * n2 - u1
    mean_u = n1 * n2 / 2.0

    # Tie correction on the variance.
    total = n1 + n2
    # counts of each distinct value
    _, counts = np.unique(combined, return_counts=True)
    tie_term = float(np.sum(counts.astype(float) ** 3 - counts.astype(float)))
    if total > 1:
        var_u = (n1 * n2 / 12.0) * ((total + 1) - tie_term / (total * (total - 1)))
    else:
        var_u = 0.0
    var_u = max(var_u, 0.0)

    if var_u > 0:
        # Continuity-corrected |z| (sign preserved by re-applying sign).
        raw = u1 - mean_u
        z_abs = (abs(raw) - 0.5) / math.sqrt(var_u)
        z = math.copysign(z_abs, raw) if raw != 0 else z_abs
        p = 2.0 * (1.0 - _normal_cdf(abs(z)))
    else:
        # No variance (all values identical): no evidence of a difference.
        z = 0.0
        p = 1.0

    rank_biserial = (2.0 * u1) / (n1 * n2) - 1.0
    return {
        "U": float(u1),
        "U_min": float(min(u1, u2)),
        "z": float(z),
        "p_two_sided": float(p),
        "rank_biserial": float(rank_biserial),
        "n1": int(n1),
        "n2": int(n2),
    }


# ----------------------------------------------------- logistic regression (numpy)
def _sigmoid(z: np.ndarray) -> np.ndarray:
    # Numerically stable sigmoid.
    out = np.empty_like(z, dtype=float)
    pos = z >= 0
    neg = ~pos
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[neg])
    out[neg] = ez / (1.0 + ez)
    return out


def _logistic_fit(
    X: np.ndarray, y: np.ndarray, lr: float = 0.1, n_iter: int = 3000,
    l2: float = 1e-2, seed: int = SEED,
) -> np.ndarray:
    """Fit L2-regularised logistic regression by gradient descent (numpy only).

    Features are standardised (mean 0, std 1) inside the fit for numerical
    stability; the returned weight vector is in the *standardised* feature
    space. A bias term is appended as the last column.
    """
    n, d = X.shape
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    Xs = (X - mu) / sd
    Xb = np.hstack([Xs, np.ones((n, 1))])
    rng = np.random.default_rng(seed)
    w = rng.normal(0.0, 0.01, size=Xb.shape[1])
    for _ in range(n_iter):
        p = _sigmoid(Xb @ w)
        grad = Xb.T @ (p - y) / n + l2 * w
        grad[-1] -= l2 * w[-1]  # do not regularise the bias
        w -= lr * grad
    return w, mu, sd


def _logistic_predict(
    w: np.ndarray, mu: np.ndarray, sd: np.ndarray, X: np.ndarray,
) -> np.ndarray:
    Xs = (X - mu) / sd
    Xb = np.hstack([Xs, np.ones((X.shape[0], 1))])
    return _sigmoid(Xb @ w)


def _auc_from_scores(scores: Sequence[float], labels: Sequence[int]) -> float:
    """AUC via the rank (Mann-Whitney) formula with mid-rank ties.

    AUC = P(score_positive > score_negative). Returns 0.5 if either class is
    empty or all scores are identical.
    """
    s = np.asarray(scores, dtype=float)
    lab = np.asarray(labels, dtype=int)
    n_pos = int(np.sum(lab == 1))
    n_neg = int(np.sum(lab == 0))
    if n_pos == 0 or n_neg == 0:
        return 0.5
    ranks = rankdata_average(s)
    sum_ranks_pos = float(ranks[lab == 1].sum())
    auc = (sum_ranks_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def logistic_regression_loo_auc(
    X: np.ndarray, y: np.ndarray, seed: int = SEED,
    lr: float = 0.1, n_iter: int = 3000, l2: float = 1e-2,
) -> dict[str, Any]:
    """Leave-one-out CV AUC for a from-scratch L2 logistic regression.

    For each of the n samples the model is re-fit on the other n-1 samples
    (seeded deterministically) and the held-out sample is scored; the AUC is
    computed over the n out-of-fold scores. Returns the AUC plus the fitted
    coefficients / scaler on the *full* data (for interpretation) and the
    out-of-fold scores.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=int)
    n = X.shape[0]
    oof = np.zeros(n, dtype=float)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        w, mu, sd = _logistic_fit(
            X[mask], y[mask], lr=lr, n_iter=n_iter, l2=l2, seed=seed,
        )
        oof[i] = float(_logistic_predict(w, mu, sd, X[i:i + 1])[0])
    auc = _auc_from_scores(oof, y)
    w_full, mu_full, sd_full = _logistic_fit(X, y, lr=lr, n_iter=n_iter, l2=l2, seed=seed)
    return {
        "auc": float(auc),
        "oof_scores": oof.tolist(),
        "n": int(n),
        "n_pos": int(np.sum(y == 1)),
        "n_neg": int(np.sum(y == 0)),
        "seed": int(seed),
        "lr": float(lr),
        "n_iter": int(n_iter),
        "l2": float(l2),
        "coeffs_standardised": w_full.tolist(),
        "feature_means": mu_full.tolist(),
        "feature_stds": sd_full.tolist(),
    }


# ----------------------------------------------------------------------- main / IO
def _median(values: Sequence[float]) -> float:
    if len(values) == 0:
        return float("nan")
    return float(np.median(np.asarray(values, dtype=float)))


def _mean(values: Sequence[float]) -> float:
    if len(values) == 0:
        return float("nan")
    return float(np.mean(np.asarray(values, dtype=float)))


def build_feature_matrix(
    windows: Sequence[dict[str, Any]], feature_names: Sequence[str],
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """Return (X, y, per_window_features) for the given feature set."""
    tied_ids = set(identify_tied_windows(windows))
    rows: list[dict[str, Any]] = []
    for w in windows:
        feats = extract_window_features(w)
        feats["tied"] = 1 if feats["window_id"] in tied_ids else 0
        rows.append(feats)
    X = np.array([[r[f] for f in feature_names] for r in rows], dtype=float)
    y = np.array([r["tied"] for r in rows], dtype=int)
    return X, y, rows


def write_csv(rows: Sequence[dict[str, Any]], path: Path = CSV_PATH) -> None:
    fieldnames = [
        "window_id", "tied",
        "speaker_count", "active_speaker_count", "active_speaker_count_ref",
        "overlap_ratio", "overlap_level", "overlap_label",
        "mixed_text_length", "separated_text_length", "total_separated_chars",
        "runtime_ratio", "avg_speaker_length_sep", "lang_id_entropy",
        "compression_ratio",
        "always_mixed_cpwer", "always_separated_cpwer", "oracle_best_cpwer",
        "router_v2_method",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def run() -> dict[str, Any]:
    with open(SOURCE_JSON, encoding="utf-8") as f:
        data = json.load(f)
    windows = data["windows"]
    n_windows = len(windows)

    tied_ids = identify_tied_windows(windows)
    tied_set = set(tied_ids)
    n_tied = len(tied_ids)
    n_nontied = n_windows - n_tied

    X, y, rows = build_feature_matrix(windows, CLASSIFIER_FEATURES)

    # Mann-Whitney per feature (tied vs non-tied).
    mwu_results: dict[str, dict[str, float]] = {}
    feature_summary: dict[str, dict[str, float]] = {}
    tied_mask = np.array([r["tied"] == 1 for r in rows], dtype=bool)
    for feat in MWU_FEATURES:
        vals = np.array([r[feat] for r in rows], dtype=float)
        t_vals = vals[tied_mask]
        nt_vals = vals[~tied_mask]
        res = mann_whitney_u(t_vals, nt_vals)
        mwu_results[feat] = res
        feature_summary[feat] = {
            "tied_mean": _mean(t_vals),
            "tied_median": _median(t_vals),
            "nontied_mean": _mean(nt_vals),
            "nontied_median": _median(nt_vals),
            "tied_min": float(np.min(t_vals)) if len(t_vals) else float("nan"),
            "tied_max": float(np.max(t_vals)) if len(t_vals) else float("nan"),
            "nontied_min": float(np.min(nt_vals)) if len(nt_vals) else float("nan"),
            "nontied_max": float(np.max(nt_vals)) if len(nt_vals) else float("nan"),
        }

    # Logistic regression LOO-CV AUC (metadata-only).
    lr_result = logistic_regression_loo_auc(X, y, seed=SEED)
    auc = lr_result["auc"]

    # Qualitative characterisation.
    silence_tied = sum(
        1 for r in rows if r["tied"] == 1 and r["mixed_text_length"] == 0 and r["separated_text_length"] == 0
    )
    silence_nontied = sum(
        1 for r in rows if r["tied"] == 0 and r["mixed_text_length"] == 0 and r["separated_text_length"] == 0
    )
    empty_mixed_tied = sum(1 for r in rows if r["tied"] == 1 and r["mixed_text_length"] == 0)
    empty_mixed_nontied = sum(1 for r in rows if r["tied"] == 0 and r["mixed_text_length"] == 0)
    single_speaker_tied = sum(1 for r in rows if r["tied"] == 1 and r["speaker_count"] == 1)
    single_speaker_nontied = sum(1 for r in rows if r["tied"] == 0 and r["speaker_count"] == 1)
    tied_at_one = sum(1 for r in rows if r["tied"] == 1 and r["always_mixed_cpwer"] == 1.0)

    # Hypothesis verdicts.
    h47a = mwu_results["active_speaker_count"]
    h47b = mwu_results["overlap_ratio"]
    h47a_supported = bool(h47a["p_two_sided"] < 0.05 and h47a["rank_biserial"] < 0)
    h47b_supported = bool(h47b["p_two_sided"] < 0.05 and h47b["rank_biserial"] < 0)
    h47c_supported = bool(auc > 0.70)

    summary = {
        "label": LABEL,
        "rq": "RQ47",
        "title": "Tied-cpWER window characterisation",
        "source_data": str(SOURCE_JSON.relative_to(PROJECT_ROOT)),
        "tie_definition": f"abs(always_mixed_cpwer - always_separated_cpwer) < {TIE_TOL}",
        "n_windows": n_windows,
        "n_tied": n_tied,
        "n_non_tied": n_nontied,
        "n_tied_at_one": tied_at_one,
        "tied_window_ids": tied_ids,
        "classifier_features": CLASSIFIER_FEATURES,
        "mwu_features": MWU_FEATURES,
        "feature_summary": feature_summary,
        "mann_whitney": mwu_results,
        "logistic_regression": {k: v for k, v in lr_result.items() if k != "oof_scores"},
        "oof_scores": lr_result["oof_scores"],
        "qualitative": {
            "silence_tied_count": silence_tied,
            "silence_nontied_count": silence_nontied,
            "empty_mixed_tied_count": empty_mixed_tied,
            "empty_mixed_nontied_count": empty_mixed_nontied,
            "single_speaker_tied_count": single_speaker_tied,
            "single_speaker_nontied_count": single_speaker_nontied,
        },
        "hypotheses": {
            "H47a": {
                "claim": "Tied windows have fewer active speakers (MWU p<0.05, effect negative)",
                "feature": "active_speaker_count",
                "p_two_sided": h47a["p_two_sided"],
                "rank_biserial": h47a["rank_biserial"],
                "supported": h47a_supported,
                "kill_condition": "p >= 0.05",
            },
            "H47b": {
                "claim": "Tied windows have lower overlap ratio (MWU p<0.05, effect negative)",
                "feature": "overlap_ratio",
                "p_two_sided": h47b["p_two_sided"],
                "rank_biserial": h47b["rank_biserial"],
                "supported": h47b_supported,
                "kill_condition": "p >= 0.05",
            },
            "H47c": {
                "claim": "Metadata-only LOO-CV logistic regression AUC > 0.70",
                "auc": auc,
                "supported": h47c_supported,
                "kill_condition": "AUC <= 0.70",
            },
        },
        "seed": SEED,
    }

    write_csv(rows, CSV_PATH)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return summary


def main() -> None:
    summary = run()
    print("=" * 72)
    print(f"RQ47: Tied-cpWER window characterisation  [{summary['label']}]")
    print("=" * 72)
    print(f"source: {summary['source_data']}")
    print(f"windows: {summary['n_windows']}  tied: {summary['n_tied']}  "
          f"non-tied: {summary['n_non_tied']}  tied@1.0: {summary['n_tied_at_one']}")
    print(f"tied window_ids: {summary['tied_window_ids']}")
    print()
    print("Mann-Whitney U (tied vs non-tied):")
    print(f"  {'feature':<28} {'p_two':>10} {'r_biserial':>12} {'tied_med':>10} {'nt_med':>10}")
    for feat in MWU_FEATURES:
        r = summary["mann_whitney"][feat]
        fs = summary["feature_summary"][feat]
        print(f"  {feat:<28} {r['p_two_sided']:>10.4g} {r['rank_biserial']:>12.3f} "
              f"{fs['tied_median']:>10.3f} {fs['nontied_median']:>10.3f}")
    print()
    print(f"Logistic regression LOO-CV AUC: {summary['logistic_regression']['auc']:.4f}")
    print()
    print("Hypothesis verdicts:")
    for h in ("H47a", "H47b", "H47c"):
        v = summary["hypotheses"][h]
        flag = "SUPPORTED" if v["supported"] else "NOT SUPPORTED (killed)"
        extra = (f"p={v['p_two_sided']:.4g} r={v['rank_biserial']:.3f}"
                 if h != "H47c" else f"AUC={v['auc']:.4f}")
        print(f"  {h}: {flag}  ({extra})")
    print()
    q = summary["qualitative"]
    print("Qualitative:")
    print(f"  silence (empty mixed & empty sep): tied={q['silence_tied_count']} "
          f"non-tied={q['silence_nontied_count']}")
    print(f"  empty mixed transcript:           tied={q['empty_mixed_tied_count']} "
          f"non-tied={q['empty_mixed_nontied_count']}")
    print(f"  single-speaker windows:           tied={q['single_speaker_tied_count']} "
          f"non-tied={q['single_speaker_nontied_count']}")
    print()
    print(f"wrote {CSV_PATH.relative_to(PROJECT_ROOT)}")
    print(f"wrote {JSON_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
