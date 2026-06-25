"""RQ19: Mode S detector — catching the monoscript hallucination residual.

REANALYSIS ONLY — no Whisper / no ASR model is run. This script reads the existing
AISHELL-4 external-validation results (``results/external_sanity_check/aishell4/
rq1_aishell4_validation_results.json``, label ``external/sanity-check``, PR #890) and
tests whether a transcript-content-similarity detector (n-gram overlap, Jaccard
similarity, length-normalized edit distance, LCS between the separated and mixed
transcripts) can catch the 2 Mode S monoscript-Chinese hallucinations that escape
every surface detector (RQ16, PR #912).

Label: experimental/frontier. Closes #914.

Background
----------
RQ16's corrected router (cpWER 1.043 vs oracle 1.017) still loses on 2 windows (22,
30): monoscript-Chinese separated hallucinations where lang-id entropy < 0.409 bits,
length ratio ~1.02, CR < 2.4 — i.e. no surface detector (which inspects the
separated track in isolation) fires. These are the "Mode S" residual. This module
asks whether comparing the separated transcript to the MIXED transcript (a second
hypothesis text from the same audio) exposes the residual.

Key empirical finding (discovered during analysis)
--------------------------------------------------
Mode S separated text is NOT gibberish — it is a near-duplicate of the mixed text
with small character substitutions (e.g. window 22: 那种→那些, 南方户→男生后). Mode S
therefore has HIGH content-similarity to mixed, opposite to diverse hallucination
(low similarity). This makes the discriminating direction non-obvious, so each
feature is calibrated TWO-SIDEDLY (both orientations tried).

The high-similarity Mode S profile is statistically DISTINCT (4 of 6 features have
permutation p < 0.05), but it is NON-DEPLOYABLE at 90% specificity because 10-13
clean single-speaker non-hallucinated tracks also have high content-similarity to
mixed (sep ≈ mix when there is no speaker reordering). Flagging both Mode S tracks
forces specificity down to 70-75%.

Method
------
For each of the 77 windows we compute six content-similarity features between the
separated transcript (per-speaker texts concatenated) and the mixed transcript:

  1. Character bigram Jaccard similarity (set of character bigrams).
  2. Character trigram Jaccard similarity.
  3. Length-normalized Levenshtein distance (edit distance / max length).
  4. Shared character ratio (|set(sep) ∩ set(mix)| / |set(sep) ∪ set(mix)|).
  5. Longest common subsequence ratio (LCS / max length).
  6. Token-overlap Jaccard (script-aware tokeniser from RQ13).

Each feature is calibrated TWO-SIDEDLY at >= 90% specificity on the 40
non-hallucinated tracks (both orientations tried). A permutation test (10,000 perms,
seed=42) on each feature tests whether Mode S has a distinct profile. The best
content-similarity detector is the feature with the lowest permutation p-value
(most distinct profile); tiebreak: highest Mode S sensitivity at 90% specificity.
A ceiling analysis reports the max Mode S sensitivity achievable at specificity
>= {0.50, 0.70, 0.80, 0.90, 0.95} to expose the deployability gap.

The best content-similarity detector (at its 90%-specificity operating point) is
OR-combined with the RQ13 language-id entropy detector (threshold 0.409 bits) and
the combined sensitivity / specificity is measured on all 77 tracks.

Hypotheses
----------
- H19a: a content-similarity detector achieves > 50% sensitivity on Mode S tracks
  at > 90% specificity.
- H19b: combining content-similarity with language-id entropy achieves > 95%
  sensitivity on all 37 hallucinated tracks.
- H19c: Mode S tracks have a distinct content-similarity profile (permutation test
  p < 0.05).

This script is pure reanalysis (numpy + stdlib only; scipy / sklearn / Whisper are
NOT required). The surface-detector primitives (``script_category``,
``language_id_entropy``, ``compression_ratio``) are lifted verbatim from RQ13/RQ16
so the Mode S definition is directly comparable.
"""
from __future__ import annotations

import csv
import json
import math
import unicodedata
import zlib
from pathlib import Path
from typing import Any, Callable

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
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "mode_s_detector"
OUT_CSV = OUT_DIR / "mode_s_results.csv"
OUT_JSON = OUT_DIR / "mode_s_results.json"

# ------------------------------------------------------------------ thresholds
LANG_ID_ENTROPY_THRESHOLD = 0.409   # RQ13 >=90%-specificity operating point
LENGTH_RATIO_THRESHOLD = 2.0        # RQ14 insertion_dominated proxy
CR_THRESHOLD = 2.4                  # Whisper default / RQ14 repetition guard
CATASTROPHIC_CPWER = 1.0            # cpWER > 1.0 => hallucination label
TARGET_SPECIFICITY = 0.90           # calibrate each detector to >= 90% specificity
N_BOOT = 10000
N_PERM = 10000
SEED = 42
EPS = 1e-9

CJK_SCRIPTS = {"Han", "Hiragana", "Katakana", "Hangul"}


# ----------------------------------------------------------------- CR primitive
def compression_ratio(text: str) -> float:
    """Whisper-style compression ratio: len(utf8 bytes) / len(zlib-compressed bytes).

    Matches ``whisper.audio.compression_ratio`` and RQ12/RQ13/RQ16. Returns 0.0 for
    empty/whitespace text. High CR (>~2.4) = repetitive loop."""
    if not text or not text.strip():
        return 0.0
    b = text.encode("utf-8")
    c = zlib.compress(b)
    return len(b) / len(c) if len(c) > 0 else 0.0


# ------------------------------------------------------------- script detection
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
    """Shannon entropy (bits) over the script-category distribution (RQ13 verbatim)."""
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


def tokenize(text: str) -> list[str]:
    """Script-aware tokeniser (RQ13 verbatim).

    CJK characters become individual character-tokens; Latin/other runs split on
    whitespace."""
    if not text:
        return []
    tokens: list[str] = []
    buf: list[str] = []
    for ch in text:
        if ch.isspace():
            if buf:
                tokens.append("".join(buf))
                buf = []
            continue
        sc = script_category(ch)
        if sc in CJK_SCRIPTS:
            if buf:
                tokens.append("".join(buf))
                buf = []
            tokens.append(ch)
        else:
            buf.append(ch)
    if buf:
        tokens.append("".join(buf))
    return tokens


# ------------------------------------------------------------- per-track aggregate
def max_across_speakers(window: dict[str, Any], fn: Callable[[str], float]) -> float:
    """Max of fn(text) over per-speaker separated transcripts (RQ12/RQ13 convention)."""
    vals = [
        fn(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


def length_ratio(window: dict[str, Any]) -> float:
    """RQ8/RQ14 silence-gap text proxy: separated_total_length / mixed_text_length."""
    sep = float(window.get("separated_total_length", 0) or 0)
    mix = float(window.get("mixed_text_length", 0) or 0)
    return sep / max(1.0, mix)


def separated_concat(window: dict[str, Any]) -> str:
    """Concatenate the per-speaker separated texts (stripped) into one string."""
    parts = [
        str(t).strip()
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return "".join(parts)


# ----------------------------------------------------------- content-similarity
def char_ngrams(text: str, n: int) -> set[str]:
    """Set of character n-grams (whitespace stripped). Returns empty set if too short."""
    s = "".join(text.split())
    if len(s) < n:
        return {s} if s else set()
    return {s[i:i + n] for i in range(len(s) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity over two sets; 0.0 if both empty."""
    if not a and not b:
        return 0.0
    u = a | b
    if not u:
        return 0.0
    return len(a & b) / len(u)


def bigram_jaccard(sep: str, mix: str) -> float:
    return jaccard(char_ngrams(sep, 2), char_ngrams(mix, 2))


def trigram_jaccard(sep: str, mix: str) -> float:
    return jaccard(char_ngrams(sep, 3), char_ngrams(mix, 3))


def levenshtein(a: str, b: str) -> int:
    """Standard O(n*m) edit distance (stdlib only). Whitespace is stripped first."""
    s1 = "".join(a.split())
    s2 = "".join(b.split())
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)
    n1, n2 = len(s1), len(s2)
    prev = list(range(n2 + 1))
    cur = [0] * (n2 + 1)
    for i in range(1, n1 + 1):
        cur[0] = i
        for j in range(1, n2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev, cur = cur, prev
    return prev[n2]


def lev_ratio(sep: str, mix: str) -> float:
    """Length-normalised edit distance: edit / max(len, 1). High = dissimilar."""
    s1 = "".join(sep.split())
    s2 = "".join(mix.split())
    m = max(len(s1), len(s2))
    if m <= 0:
        return 0.0
    return levenshtein(s1, s2) / m


def shared_char_ratio(sep: str, mix: str) -> float:
    """|set(sep chars) ∩ set(mix chars)| / |union|. High = same character inventory."""
    a = {c for c in sep if not c.isspace()}
    b = {c for c in mix if not c.isspace()}
    return jaccard(a, b)


def lcs_length(a: str, b: str) -> int:
    """Longest common subsequence length (O(n*m) DP, stdlib only)."""
    s1 = "".join(a.split())
    s2 = "".join(b.split())
    n1, n2 = len(s1), len(s2)
    if n1 == 0 or n2 == 0:
        return 0
    prev = [0] * (n2 + 1)
    cur = [0] * (n2 + 1)
    for i in range(1, n1 + 1):
        for j in range(1, n2 + 1):
            if s1[i - 1] == s2[j - 1]:
                cur[j] = prev[j - 1] + 1
            else:
                cur[j] = max(prev[j], cur[j - 1])
        prev, cur = cur, prev
    return prev[n2]


def lcs_ratio(sep: str, mix: str) -> float:
    """LCS / max(len, 1). High = sep is a subsequence of mix (near-duplicate)."""
    s1 = "".join(sep.split())
    s2 = "".join(mix.split())
    m = max(len(s1), len(s2))
    if m <= 0:
        return 0.0
    return lcs_length(s1, s2) / m


def token_overlap_jaccard(sep: str, mix: str) -> float:
    """Jaccard over script-aware token sets (RQ13 tokeniser)."""
    return jaccard(set(tokenize(sep)), set(tokenize(mix)))


# --------------------------------------------------------- threshold calibration
def calibrate_two_sided(
    neg_scores: list[float],
    pos_scores_mode_s: list[float],
    pos_scores_all_halluc: list[float],
    target_spec: float = TARGET_SPECIFICITY,
) -> dict[str, Any]:
    """Calibrate a single feature TWO-SIDEDLY at >= target_spec specificity.

    Tries both orientations:
      - "high": flag if score >= threshold (high score = hallucination)
      - "low":  flag if score <= threshold (low score = hallucination)
    For each orientation, candidate thresholds = all unique scores; specificity is
    measured on neg_scores (non-hallucinated). Among operating points with
    specificity >= target_spec, the one with maximal Mode S sensitivity is kept
    (tiebreak: maximal all-hallucinated sensitivity, then maximal specificity).
    """
    n_neg = len(neg_scores)
    n_ms = len(pos_scores_mode_s)
    n_ah = len(pos_scores_all_halluc)
    candidates = sorted(set(neg_scores) | set(pos_scores_mode_s) | set(pos_scores_all_halluc))
    best: dict[str, Any] | None = None

    for direction in ("high", "low"):
        for t in candidates:
            if direction == "high":
                fp = sum(1 for s in neg_scores if s >= t - EPS)
                tp_ms = sum(1 for s in pos_scores_mode_s if s >= t - EPS)
                tp_ah = sum(1 for s in pos_scores_all_halluc if s >= t - EPS)
            else:  # "low"
                fp = sum(1 for s in neg_scores if s <= t + EPS)
                tp_ms = sum(1 for s in pos_scores_mode_s if s <= t + EPS)
                tp_ah = sum(1 for s in pos_scores_all_halluc if s <= t + EPS)
            spec = 1.0 - (fp / n_neg) if n_neg else 1.0
            sens_ms = (tp_ms / n_ms) if n_ms else 0.0
            sens_ah = (tp_ah / n_ah) if n_ah else 0.0
            if spec < target_spec - EPS:
                continue
            cand = {
                "direction": direction,
                "threshold": float(t),
                "specificity": float(spec),
                "sensitivity_mode_s": float(sens_ms),
                "sensitivity_all_hallucinated": float(sens_ah),
                "tp_mode_s": int(tp_ms), "fp": int(fp),
                "tn": int(n_neg - fp), "fn_mode_s": int(n_ms - tp_ms),
                "tp_all_hallucinated": int(tp_ah),
                "fn_all_hallucinated": int(n_ah - tp_ah),
            }
            if best is None:
                best = cand
                continue
            better = (
                sens_ms > best["sensitivity_mode_s"] + EPS
                or (abs(sens_ms - best["sensitivity_mode_s"]) <= EPS
                    and sens_ah > best["sensitivity_all_hallucinated"] + EPS)
                or (abs(sens_ms - best["sensitivity_mode_s"]) <= EPS
                    and abs(sens_ah - best["sensitivity_all_hallucinated"]) <= EPS
                    and spec > best["specificity"] + EPS)
            )
            if better:
                best = cand
    if best is None:
        best = {
            "direction": "none",
            "threshold": float("inf"),
            "specificity": 1.0,
            "sensitivity_mode_s": 0.0,
            "sensitivity_all_hallucinated": 0.0,
            "tp_mode_s": 0, "fp": 0, "tn": int(n_neg), "fn_mode_s": int(n_ms),
            "tp_all_hallucinated": 0, "fn_all_hallucinated": int(n_ah),
        }
    return best


def flag_at(score: float, direction: str, threshold: float) -> bool:
    """Apply a calibrated two-sided operating point to a single score."""
    if direction == "high":
        return score >= threshold - EPS
    if direction == "low":
        return score <= threshold + EPS
    return False


def ceiling_analysis(
    neg_scores: list[float],
    pos_scores_mode_s: list[float],
    spec_floors: list[float],
) -> list[dict[str, Any]]:
    """Max Mode S sensitivity achievable at specificity >= each floor (two-sided).

    Exposes the deployability gap: how much specificity must be sacrificed to catch
    Mode S. For each spec floor, searches both orientations and all thresholds."""
    n_neg = len(neg_scores)
    n_ms = len(pos_scores_mode_s)
    candidates = sorted(set(neg_scores) | set(pos_scores_mode_s))
    out: list[dict[str, Any]] = []
    for floor in spec_floors:
        best_sens = 0.0
        best_dir = "none"
        best_t = float("inf")
        best_spec = 1.0
        for direction in ("high", "low"):
            for t in candidates:
                if direction == "high":
                    fp = sum(1 for s in neg_scores if s >= t - EPS)
                    tp_ms = sum(1 for s in pos_scores_mode_s if s >= t - EPS)
                else:
                    fp = sum(1 for s in neg_scores if s <= t + EPS)
                    tp_ms = sum(1 for s in pos_scores_mode_s if s <= t + EPS)
                spec = 1.0 - (fp / n_neg) if n_neg else 1.0
                sens = (tp_ms / n_ms) if n_ms else 0.0
                if spec >= floor - EPS and sens > best_sens + EPS:
                    best_sens = sens
                    best_dir = direction
                    best_t = float(t)
                    best_spec = spec
        out.append({
            "specificity_floor": floor,
            "max_sensitivity_mode_s": round(best_sens, 6),
            "direction": best_dir,
            "threshold": round(best_t, 6),
            "achieved_specificity": round(best_spec, 6),
        })
    return out


# --------------------------------------------------------------------- bootstrap
def bootstrap_sensitivity_ci(
    scores: np.ndarray, labels: np.ndarray, direction: str, threshold: float,
    n_boot: int = N_BOOT, seed: int = SEED,
) -> tuple[float, float]:
    """Bootstrap 95% CI for sensitivity = P(flag | label==1) with FIXED threshold."""
    rng = np.random.default_rng(seed)
    n = len(scores)
    sens: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        s = scores[idx]
        lab = labels[idx]
        n_pos = int(lab.sum())
        if n_pos <= 0:
            continue
        if direction == "high":
            tp = int(((s >= threshold - EPS) & (lab == 1)).sum())
        else:
            tp = int(((s <= threshold + EPS) & (lab == 1)).sum())
        sens.append(tp / n_pos)
    if not sens:
        return 0.0, 0.0
    return float(np.percentile(sens, 2.5)), float(np.percentile(sens, 97.5))


def bootstrap_specificity_ci(
    scores: np.ndarray, labels: np.ndarray, direction: str, threshold: float,
    n_boot: int = N_BOOT, seed: int = SEED,
) -> tuple[float, float]:
    """Bootstrap 95% CI for specificity = P(not flag | label==0) with FIXED threshold."""
    rng = np.random.default_rng(seed)
    n = len(scores)
    specs: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        s = scores[idx]
        lab = labels[idx]
        n_neg = int((lab == 0).sum())
        if n_neg <= 0:
            continue
        if direction == "high":
            fp = int(((s >= threshold - EPS) & (lab == 0)).sum())
        else:
            fp = int(((s <= threshold + EPS) & (lab == 0)).sum())
        specs.append(1.0 - fp / n_neg)
    if not specs:
        return 0.0, 0.0
    return float(np.percentile(specs, 2.5)), float(np.percentile(specs, 97.5))


# -------------------------------------------------------------- permutation test
def permutation_test(
    feature_values: np.ndarray, mode_s_mask: np.ndarray,
    n_perm: int = N_PERM, seed: int = SEED,
) -> dict[str, Any]:
    """Permutation test for a distinct Mode S content-similarity profile.

    Test statistic = mean(feature | Mode S) - mean(feature | not Mode S). The label
    is permuted among the 77 tracks (n_perm resamples, seed). p-value (two-sided) =
    fraction of permutations with |stat| >= |observed|, with +1 smoothing. With n=2
    Mode S the resolution is bounded by C(77,2)=2926 distinct labelings."""
    n = len(feature_values)
    n_ms = int(mode_s_mask.sum())
    obs_ms_mean = float(feature_values[mode_s_mask].mean()) if n_ms > 0 else 0.0
    obs_other_mean = float(feature_values[~mode_s_mask].mean()) if n_ms < n else 0.0
    obs_stat = obs_ms_mean - obs_other_mean

    rng = np.random.default_rng(seed)
    count_extreme = 0
    for _ in range(n_perm):
        perm_idx = rng.permutation(n)
        perm_mask = np.zeros(n, dtype=bool)
        perm_mask[perm_idx[:n_ms]] = True
        if perm_mask.sum() == 0 or perm_mask.sum() == n:
            continue
        ms_mean = float(feature_values[perm_mask].mean())
        other_mean = float(feature_values[~perm_mask].mean())
        stat = ms_mean - other_mean
        if abs(stat) >= abs(obs_stat) - EPS:
            count_extreme += 1
    p_value = (count_extreme + 1) / (n_perm + 1)
    return {
        "test_statistic": round(obs_stat, 6),
        "mode_s_mean": round(obs_ms_mean, 6),
        "others_mean": round(obs_other_mean, 6),
        "n_perm": n_perm,
        "n_mode_s": n_ms,
        "n_others": n - n_ms,
        "p_value_two_sided": round(p_value, 6),
        "n_extreme": count_extreme,
        "n_distinct_labelings": math.comb(n, n_ms),
        "note": (
            "Two-sided permutation test: fraction of permutations with |stat| >= |observed|. "
            f"With n_mode_s={n_ms} the number of distinct labelings is C({n},{n_ms})="
            f"{math.comb(n, n_ms)}; p-value resolution is bounded and reported with +1 smoothing."
        ),
    }


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]
    n = len(windows)

    # --- per-window surface features + labels + content-similarity features
    rows: list[dict[str, Any]] = []
    for w in windows:
        sep_cpwer = float(w["always_separated_cpwer"])
        mixed_cpwer = float(w["always_mixed_cpwer"])
        ent = max_across_speakers(w, language_id_entropy)
        mcr = max_across_speakers(w, compression_ratio)
        lr = length_ratio(w)
        halluc = sep_cpwer > CATASTROPHIC_CPWER
        mode_s = (halluc and ent < LANG_ID_ENTROPY_THRESHOLD
                  and lr < LENGTH_RATIO_THRESHOLD and mcr < CR_THRESHOLD)

        sep_text = separated_concat(w)
        mix_text = str(w.get("mixed_text", "") or "")
        bj = bigram_jaccard(sep_text, mix_text)
        tj = trigram_jaccard(sep_text, mix_text)
        lv = lev_ratio(sep_text, mix_text)
        sc = shared_char_ratio(sep_text, mix_text)
        lc = lcs_ratio(sep_text, mix_text)
        to = token_overlap_jaccard(sep_text, mix_text)

        rows.append({
            "window_id": w["window_id"],
            "always_separated_cpwer": round(sep_cpwer, 6),
            "always_mixed_cpwer": round(mixed_cpwer, 6),
            "hallucinated": bool(halluc),
            "mode_s": bool(mode_s),
            "lang_id_entropy": round(ent, 6),
            "length_ratio": round(lr, 6),
            "cr": round(mcr, 6),
            "bigram_jaccard": round(bj, 6),
            "trigram_jaccard": round(tj, 6),
            "lev_ratio": round(lv, 6),
            "shared_char_ratio": round(sc, 6),
            "lcs_ratio": round(lc, 6),
            "token_overlap_jaccard": round(to, 6),
            "num_speakers": w["num_speakers"],
            "_sep_text": sep_text,
            "_mix_text": mix_text,
        })

    n_halluc = sum(1 for r in rows if r["hallucinated"])
    n_nonhalluc = n - n_halluc
    n_mode_s = sum(1 for r in rows if r["mode_s"])
    mode_s_ids = [r["window_id"] for r in rows if r["mode_s"]]

    # --- calibrate each content-similarity feature two-sidedly + permutation test
    feat_specs = [
        ("bigram_jaccard", "bigram_jaccard", "H19a", "character bigram Jaccard similarity"),
        ("trigram_jaccard", "trigram_jaccard", None, "character trigram Jaccard similarity"),
        ("lev_ratio", "lev_ratio", None, "length-normalised Levenshtein distance"),
        ("shared_char_ratio", "shared_char_ratio", None, "shared character ratio (set Jaccard)"),
        ("lcs_ratio", "lcs_ratio", None, "longest common subsequence ratio"),
        ("token_overlap_jaccard", "token_overlap_jaccard", None, "token-overlap Jaccard"),
    ]
    detector_results: list[dict[str, Any]] = []
    for name, key, hypo, note in feat_specs:
        scores = [r[key] for r in rows]
        neg = [float(s) for s, r in zip(scores, rows) if not r["hallucinated"]]
        pos_ms = [float(s) for s, r in zip(scores, rows) if r["mode_s"]]
        pos_ah = [float(s) for s, r in zip(scores, rows) if r["hallucinated"]]
        op = calibrate_two_sided(neg, pos_ms, pos_ah, TARGET_SPECIFICITY)
        # permutation test on this feature
        feat_arr = np.array(scores, dtype=float)
        ms_mask = np.array([r["mode_s"] for r in rows], dtype=bool)
        perm = permutation_test(feat_arr, ms_mask, N_PERM, SEED)
        # bootstrap CIs (fixed threshold)
        scores_arr = np.array(scores, dtype=float)
        ms_labels = np.array([1.0 if r["mode_s"] else 0.0 for r in rows], dtype=float)
        ah_labels = np.array([1.0 if r["hallucinated"] else 0.0 for r in rows], dtype=float)
        neg_labels = np.array([0.0 if r["hallucinated"] else 1.0 for r in rows], dtype=float)
        ci_ms_lo, ci_ms_hi = bootstrap_sensitivity_ci(
            scores_arr, ms_labels, op["direction"], op["threshold"])
        ci_ah_lo, ci_ah_hi = bootstrap_sensitivity_ci(
            scores_arr, ah_labels, op["direction"], op["threshold"])
        spec_ci_lo, spec_ci_hi = bootstrap_specificity_ci(
            scores_arr, neg_labels, op["direction"], op["threshold"])
        # ceiling analysis (max Mode S sens at lower spec floors)
        ceil = ceiling_analysis(neg, pos_ms, [0.50, 0.70, 0.80, 0.90, 0.95])
        detector_results.append({
            "detector": name,
            "hypothesis": hypo,
            "note": note,
            "feature_key": key,
            "direction": op["direction"],
            "direction_meaning": (
                "flag if score >= threshold (high score = hallucination)"
                if op["direction"] == "high"
                else "flag if score <= threshold (low score = hallucination)"
                if op["direction"] == "low" else "no threshold met 90% specificity target"
            ),
            "threshold": round(op["threshold"], 6),
            "specificity": round(op["specificity"], 6),
            "specificity_ci_95": [round(spec_ci_lo, 6), round(spec_ci_hi, 6)],
            "sensitivity_mode_s": round(op["sensitivity_mode_s"], 6),
            "sensitivity_mode_s_ci_95": [round(ci_ms_lo, 6), round(ci_ms_hi, 6)],
            "sensitivity_all_hallucinated": round(op["sensitivity_all_hallucinated"], 6),
            "sensitivity_all_hallucinated_ci_95": [round(ci_ah_lo, 6), round(ci_ah_hi, 6)],
            "tp_mode_s": op["tp_mode_s"], "fp": op["fp"],
            "tn": op["tn"], "fn_mode_s": op["fn_mode_s"],
            "tp_all_hallucinated": op["tp_all_hallucinated"],
            "fn_all_hallucinated": op["fn_all_hallucinated"],
            "permutation_test": perm,
            "ceiling_analysis": ceil,
            "n_mode_s": n_mode_s, "n_all_hallucinated": n_halluc, "n_nonhallucinated": n_nonhalluc,
        })

    # --- best content-similarity detector: most distinct profile (lowest perm p),
    #     tiebreak highest sens_ms at 90% spec, then highest sens_ah.
    best = min(
        detector_results,
        key=lambda d: (d["permutation_test"]["p_value_two_sided"],
                       -d["sensitivity_mode_s"],
                       -d["sensitivity_all_hallucinated"]),
    )
    best_key = best["feature_key"]
    best_dir = best["direction"]
    best_thr = best["threshold"]
    best_detector_name = best["detector"]

    # per-window best-detector flag (at the 90%-specificity operating point)
    for r in rows:
        r["best_detector_flag"] = bool(flag_at(r[best_key], best_dir, best_thr))

    # --- combined detector: best content-similarity (90% spec op point) OR lang-id > 0.409
    combined_flags: list[bool] = []
    for r in rows:
        cs_flag = bool(flag_at(r[best_key], best_dir, best_thr))
        lang_flag = r["lang_id_entropy"] > LANG_ID_ENTROPY_THRESHOLD
        combined_flags.append(cs_flag or lang_flag)

    tp_comb_ah = sum(1 for r, f in zip(rows, combined_flags) if r["hallucinated"] and f)
    fp_comb = sum(1 for r, f in zip(rows, combined_flags) if not r["hallucinated"] and f)
    tn_comb = sum(1 for r, f in zip(rows, combined_flags) if not r["hallucinated"] and not f)
    fn_comb_ah = sum(1 for r, f in zip(rows, combined_flags) if r["hallucinated"] and not f)
    comb_sens_ah = tp_comb_ah / n_halluc if n_halluc else 0.0
    comb_spec = tn_comb / n_nonhalluc if n_nonhalluc else 0.0
    tp_comb_ms = sum(1 for r, f in zip(rows, combined_flags) if r["mode_s"] and f)
    comb_sens_ms = tp_comb_ms / n_mode_s if n_mode_s else 0.0

    # combined bootstrap CIs (fixed thresholds)
    cs_scores = np.array([r[best_key] for r in rows], dtype=float)
    lang_scores = np.array([r["lang_id_entropy"] for r in rows], dtype=float)
    ah_labels = np.array([1.0 if r["hallucinated"] else 0.0 for r in rows], dtype=float)
    rng = np.random.default_rng(SEED)
    comb_sens_boot: list[float] = []
    comb_spec_boot: list[float] = []
    for _ in range(N_BOOT):
        idx = rng.integers(0, n, size=n)
        s_cs = cs_scores[idx]
        s_lang = lang_scores[idx]
        lab = ah_labels[idx]
        if best_dir == "high":
            flag = (s_cs >= best_thr - EPS) | (s_lang > LANG_ID_ENTROPY_THRESHOLD)
        elif best_dir == "low":
            flag = (s_cs <= best_thr + EPS) | (s_lang > LANG_ID_ENTROPY_THRESHOLD)
        else:
            flag = s_lang > LANG_ID_ENTROPY_THRESHOLD
        n_pos = int(lab.sum())
        n_neg_b = int((lab == 0).sum())
        if n_pos > 0:
            comb_sens_boot.append(int((flag & (lab == 1)).sum()) / n_pos)
        if n_neg_b > 0:
            comb_spec_boot.append(1.0 - int((flag & (lab == 0)).sum()) / n_neg_b)
    comb_sens_ci = [round(float(np.percentile(comb_sens_boot, 2.5)), 6),
                    round(float(np.percentile(comb_sens_boot, 97.5)), 6)] if comb_sens_boot else [0.0, 0.0]
    comb_spec_ci = [round(float(np.percentile(comb_spec_boot, 2.5)), 6),
                    round(float(np.percentile(comb_spec_boot, 97.5)), 6)] if comb_spec_boot else [0.0, 0.0]

    # --- lang-id entropy alone (reference)
    tp_lang_ah = sum(1 for r in rows if r["hallucinated"] and r["lang_id_entropy"] > LANG_ID_ENTROPY_THRESHOLD)
    fp_lang = sum(1 for r in rows if not r["hallucinated"] and r["lang_id_entropy"] > LANG_ID_ENTROPY_THRESHOLD)
    tp_lang_ms = sum(1 for r in rows if r["mode_s"] and r["lang_id_entropy"] > LANG_ID_ENTROPY_THRESHOLD)
    lang_sens_ah = tp_lang_ah / n_halluc if n_halluc else 0.0
    lang_spec = (n_nonhalluc - fp_lang) / n_nonhalluc if n_nonhalluc else 0.0
    lang_sens_ms = tp_lang_ms / n_mode_s if n_mode_s else 0.0

    # --- hypothesis verdicts
    h19a_supported = best["sensitivity_mode_s"] > 0.5 and best["specificity"] > 0.9
    h19b_supported = comb_sens_ah > 0.95
    h19c_supported = best["permutation_test"]["p_value_two_sided"] < 0.05

    # how many features have distinct profiles (perm p < 0.05)
    n_features_distinct = sum(1 for d in detector_results
                              if d["permutation_test"]["p_value_two_sided"] < 0.05)

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ19: Mode S detector — content-similarity for the monoscript hallucination residual",
        "closes_issue": 914,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "method": (
            "reanalysis only (no Whisper / no ASR run); content-similarity features computed "
            "between the separated transcript (per-speaker texts concatenated) and the mixed "
            "transcript. Each feature calibrated two-sidedly at >= 90% specificity on the 40 "
            "non-hallucinated tracks. Best detector = lowest permutation p-value (most distinct "
            "Mode S profile). Combined = best content-similarity (at 90% spec) OR lang-id entropy."
        ),
        "meeting_id": data["meeting_id"],
        "n_windows": n,
        "n_hallucinated_tracks": n_halluc,
        "n_nonhallucinated_tracks": n_nonhalluc,
        "n_mode_s_tracks": n_mode_s,
        "mode_s_window_ids": mode_s_ids,
        "hallucination_label": "always_separated_cpwer > 1.0 (37/40 split, RQ12)",
        "mode_s_definition": (
            "hallucinated AND lang_id_entropy < 0.409 AND length_ratio < 2.0 AND cr < 2.4 "
            "(escapes every surface detector; the RQ16 corrected-router residual)"
        ),
        "mode_s_context": {
            "rq16_corrected_router_cpwer": 1.0433,
            "rq16_oracle_cpwer": 1.0173,
            "rq16_residual_gap": 0.0260,
            "mode_s_mechanism": (
                "Mode S separated text is a near-duplicate of the mixed text with small character "
                "substitutions (e.g. window 22: 那种→那些, 南方户→男生后; window 30: 說說大好→那個都給包包包). "
                "It is NOT gibberish. Mode S therefore has HIGH content-similarity to mixed, "
                "opposite to diverse hallucination (low similarity)."
            ),
            "confound": (
                "10-13 clean single-speaker (or 2-speaker) non-hallucinated tracks ALSO have high "
                "content-similarity to mixed (sep ≈ mix when there is no speaker reordering). "
                "Flagging both Mode S tracks therefore forces specificity down to 70-75%, below "
                "the 90% target. This is why a statistically distinct profile (H19c) is not "
                "deployable (H19a/H19b)."
            ),
        },
        "thresholds": {
            "lang_id_entropy": LANG_ID_ENTROPY_THRESHOLD,
            "length_ratio": LENGTH_RATIO_THRESHOLD,
            "cr": CR_THRESHOLD,
            "target_specificity": TARGET_SPECIFICITY,
        },
        "detectors": detector_results,
        "best_content_similarity_detector": {
            "detector": best_detector_name,
            "feature_key": best_key,
            "selection_rule": "lowest permutation p-value (most distinct Mode S profile); tiebreak highest Mode S sensitivity at 90% specificity",
            "direction": best_dir,
            "threshold": round(best_thr, 6),
            "specificity_at_90pct_target": best["specificity"],
            "sensitivity_mode_s_at_90pct_target": best["sensitivity_mode_s"],
            "sensitivity_all_hallucinated_at_90pct_target": best["sensitivity_all_hallucinated"],
            "permutation_p_value": best["permutation_test"]["p_value_two_sided"],
            "ceiling_analysis": best["ceiling_analysis"],
            "ceiling_interpretation": (
                "Max Mode S sensitivity achievable as the specificity floor is relaxed. "
                "At >= 90% specificity the best detector catches 0% of Mode S; catching 100% "
                "requires dropping specificity to ~75%."
            ),
        },
        "lang_id_entropy_alone_reference": {
            "threshold": LANG_ID_ENTROPY_THRESHOLD,
            "specificity": round(lang_spec, 6),
            "sensitivity_all_hallucinated": round(lang_sens_ah, 6),
            "sensitivity_mode_s": round(lang_sens_ms, 6),
            "tp_all_hallucinated": tp_lang_ah, "fp": fp_lang,
            "note": "RQ13 lang-id entropy detector (no content-similarity). By definition Mode S escapes it (lang-id < 0.409), so lang-id alone misses both Mode S tracks.",
        },
        "combined_detector": {
            "rule": f"({best_detector_name} flag at 90% spec) OR (lang_id_entropy > {LANG_ID_ENTROPY_THRESHOLD})",
            "specificity": round(comb_spec, 6),
            "specificity_ci_95": comb_spec_ci,
            "sensitivity_all_hallucinated": round(comb_sens_ah, 6),
            "sensitivity_all_hallucinated_ci_95": comb_sens_ci,
            "sensitivity_mode_s": round(comb_sens_ms, 6),
            "tp_all_hallucinated": tp_comb_ah,
            "fp": fp_comb, "tn": tn_comb, "fn_all_hallucinated": fn_comb_ah,
            "tp_mode_s": tp_comb_ms,
            "note": (
                "At 90% specificity the best content-similarity detector flags 0 Mode S tracks, "
                "so the combined detector equals lang-id entropy alone (94.6% sensitivity on the "
                "37 hallucinated, 0% on Mode S). Content-similarity adds nothing deployable."
            ),
        },
        "hypothesis_verdicts": {
            "H19a": {
                "statement": "a content-similarity detector achieves > 50% sensitivity on Mode S tracks at > 90% specificity",
                "best_detector": best_detector_name,
                "sensitivity_mode_s": best["sensitivity_mode_s"],
                "specificity": best["specificity"],
                "bootstrap_ci_95_mode_s_sensitivity": best["sensitivity_mode_s_ci_95"],
                "ceiling_analysis": best["ceiling_analysis"],
                "supported": bool(h19a_supported),
                "reason": (
                    f"At >= 90% specificity the best content-similarity detector ({best_detector_name}) "
                    f"catches {best['sensitivity_mode_s']:.0%} of Mode S. Catching 100% of Mode S "
                    f"requires specificity ~75% (see ceiling_analysis). The Mode S high-similarity "
                    f"profile is confounded with clean single-speaker non-hallucinated tracks."
                ),
            },
            "H19b": {
                "statement": "combining content-similarity with language-id entropy achieves > 95% sensitivity on all 37 hallucinated tracks",
                "combined_sensitivity_all_hallucinated": round(comb_sens_ah, 6),
                "combined_specificity": round(comb_spec, 6),
                "bootstrap_ci_95_sensitivity": comb_sens_ci,
                "lang_id_alone_sensitivity": round(lang_sens_ah, 6),
                "supported": bool(h19b_supported),
                "reason": (
                    f"Combined sensitivity is {comb_sens_ah:.1%} ({tp_comb_ah}/37); lang-id alone "
                    f"is {lang_sens_ah:.1%} ({tp_lang_ah}/37). Content-similarity adds 0 Mode S "
                    f"tracks at 90% specificity, so the combined detector equals lang-id alone and "
                    f"misses the > 95% target by 1 track."
                ),
            },
            "H19c": {
                "statement": "Mode S tracks have a distinct content-similarity profile (permutation test p < 0.05)",
                "best_feature": best_key,
                "test_statistic": best["permutation_test"]["test_statistic"],
                "mode_s_mean": best["permutation_test"]["mode_s_mean"],
                "others_mean": best["permutation_test"]["others_mean"],
                "p_value_two_sided": best["permutation_test"]["p_value_two_sided"],
                "n_extreme": best["permutation_test"]["n_extreme"],
                "n_features_with_p_lt_0p05": n_features_distinct,
                "n_features_total": len(detector_results),
                "all_features_p_values": {
                    d["detector"]: d["permutation_test"]["p_value_two_sided"]
                    for d in detector_results
                },
                "supported": bool(h19c_supported),
                "reason": (
                    f"Best feature {best_key} permutation p={best['permutation_test']['p_value_two_sided']:.4f} "
                    f"({best['permutation_test']['n_extreme']}/{N_PERM} extreme). "
                    f"{n_features_distinct} of {len(detector_results)} features have p < 0.05 "
                    f"(bigram_jaccard, shared_char_ratio, lcs_ratio, token_overlap_jaccard). Mode S "
                    f"is MORE similar to mixed than other tracks (near-duplicate), which is a "
                    f"distinct profile — but distinct in the high-similarity direction, confounded "
                    f"with clean single-speaker tracks."
                ),
            },
        },
    }

    # --- write CSV (per-window)
    csv_fields = [
        "window_id", "hallucinated", "mode_s",
        "lang_id_entropy", "length_ratio", "cr",
        "bigram_jaccard", "trigram_jaccard", "lev_ratio",
        "shared_char_ratio", "lcs_ratio", "token_overlap_jaccard",
        "best_detector_flag",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, "") for k in csv_fields})

    # --- write JSON (summary + per-window)
    summary_with_rows = dict(summary)
    summary_with_rows["per_window"] = [
        {k: v for k, v in r.items() if not k.startswith("_")} for r in rows
    ]
    OUT_JSON.write_text(
        json.dumps(summary_with_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # --- console
    print(f"=== RQ19: Mode S detector (AISHELL-4, {n} tracks) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Hallucinated: {n_halluc}  |  non-hallucinated: {n_nonhalluc}  |  Mode S: {n_mode_s}")
    print(f"Mode S window ids: {mode_s_ids}")
    print(f"Target specificity: {TARGET_SPECIFICITY:.0%}  |  calibration: two-sided")
    print()
    print(f"{'detector':24s} {'dir':>5s} {'thresh':>9s} {'spec':>6s} {'sens_MS':>8s} {'sens_AH':>8s} {'perm_p':>8s}")
    for d in detector_results:
        print(f"{d['detector']:24s} {d['direction']:>5s} {d['threshold']:9.4f} "
              f"{d['specificity']:6.1%} {d['sensitivity_mode_s']:8.1%} "
              f"{d['sensitivity_all_hallucinated']:8.1%} "
              f"{d['permutation_test']['p_value_two_sided']:8.4f}")
    print()
    print(f"Best content-similarity detector: {best_detector_name} "
          f"(perm p={best['permutation_test']['p_value_two_sided']:.4f})")
    print(f"  at 90% spec: dir={best_dir}, thresh={best_thr:.4f}, "
          f"sens_MS={best['sensitivity_mode_s']:.1%}, sens_AH={best['sensitivity_all_hallucinated']:.1%}")
    print(f"  ceiling (max sens_MS by spec floor):")
    for c in best["ceiling_analysis"]:
        print(f"    spec>={c['specificity_floor']:.2f}: sens_MS={c['max_sensitivity_mode_s']:.1%} "
              f"(dir={c['direction']}, achieved spec={c['achieved_specificity']:.1%})")
    print(f"Lang-id entropy alone: spec={lang_spec:.1%}, sens_AH={lang_sens_ah:.1%} ({tp_lang_ah}/{n_halluc}), "
          f"sens_MS={lang_sens_ms:.1%} ({tp_lang_ms}/{n_mode_s})")
    print(f"Combined ({best_detector_name} OR lang-id) at 90% spec: "
          f"spec={comb_spec:.1%}, sens_AH={comb_sens_ah:.1%} ({tp_comb_ah}/{n_halluc}), "
          f"sens_MS={comb_sens_ms:.1%} ({tp_comb_ms}/{n_mode_s})")
    print()
    print("Hypothesis verdicts:")
    print(f"  H19a (content-sim sens_MS > 50% at spec > 90%): "
          f"{'SUPPORTED' if h19a_supported else 'NOT SUPPORTED'} "
          f"(sens_MS={best['sensitivity_mode_s']:.1%}, spec={best['specificity']:.1%})")
    print(f"  H19b (combined sens_AH > 95%): "
          f"{'SUPPORTED' if h19b_supported else 'NOT SUPPORTED'} "
          f"(sens_AH={comb_sens_ah:.1%}, spec={comb_spec:.1%})")
    print(f"  H19c (Mode S distinct profile, perm p < 0.05): "
          f"{'SUPPORTED' if h19c_supported else 'NOT SUPPORTED'} "
          f"(p={best['permutation_test']['p_value_two_sided']:.4f}, "
          f"{n_features_distinct}/{len(detector_results)} features p<0.05)")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
