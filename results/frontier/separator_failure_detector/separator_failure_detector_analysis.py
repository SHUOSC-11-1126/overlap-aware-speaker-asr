"""RQ22: Separator-failure detector — per-speaker transcript structure for Mode S.

REANALYSIS ONLY — no Whisper / no ASR model is run. This script reads the existing
AISHELL-4 external-validation results (``results/external_sanity_check/aishell4/
rq1_aishell4_validation_results.json``, label ``external/sanity-check``, PR #890) and
tests whether per-speaker transcript structure (per-speaker length distribution,
speaker-attribution consistency, sep-to-mix metadata) can catch the 2 Mode S
monoscript-Chinese hallucinations that escape every surface detector (RQ16, PR #912)
AND every content-similarity detector (RQ19, PR #919).

Label: experimental/frontier. Closes #920.

Background
----------
RQ19's content-similarity detectors are statistically distinct on Mode S (4 of 6
features have permutation p < 0.05) but NON-DEPLOYABLE at 90% specificity because
10-13 clean single-speaker non-hallucinated tracks also have high content-similarity
to mixed (sep approx equals mix when there is no speaker reordering). RQ19's
limitation #5 suggested that per-speaker structure might break this confound: instead
of comparing the AGGREGATE separated transcript to mixed, inspect how the separated
text is DISTRIBUTED across the per-speaker channels. Mode S is mechanistically a
separator failure (the separator returned one near-duplicate of mixed in a single
speaker channel and left the other channels empty), so its per-speaker profile should
look like ONE speaker carrying the whole mixed transcript rather than a genuine
multi-speaker split.

Method
------
For each of the 77 windows we compute seven per-speaker-structure features computed
from ``separated_text_per_speaker`` and the mixed-track metadata:

  1. per_speaker_length_entropy — Shannon entropy (bits) over the normalised
     per-speaker separated text lengths. Low = one speaker dominates.
  2. per_speaker_length_gini — Gini coefficient of per-speaker separated text
     lengths. High = unequal split.
  3. sep_to_mix_length_ratio — separated_total_length / mixed_text_length
     (Mode S hypothesis: approx 1.02).
  4. sep_to_mix_runtime_ratio — separated_runtime_sec / mixed_runtime_sec.
  5. speaker_attribution_consistency — fraction of non-empty per-speaker separated
     texts that appear as a contiguous substring of the mixed text (whitespace
     stripped on both sides). High = the separator output is a faithful contiguous
     span of mixed; low = the separator output is a re-decoded / re-ordered version.
  6. per_speaker_overlap_fraction — fraction of non-empty speaker pairs whose
     separated texts share at least one non-whitespace character.
  7. effective_speaker_count — number of distinct non-empty per-speaker separated
     texts.

Each feature is calibrated TWO-SIDEDLY at >= 90% specificity on the 40
non-hallucinated tracks (both orientations tried, Mode S sensitivity maximised).
A permutation test (10,000 perms, seed=42, two-sided, +1 smoothing) on each feature
tests whether Mode S has a distinct profile. The best per-speaker-structure detector
is the feature with the lowest permutation p-value (most distinct profile); tiebreak:
highest Mode S sensitivity at 90% specificity. A ceiling analysis reports the max
Mode S sensitivity achievable at specificity >= {0.50, 0.70, 0.80, 0.90, 0.95} to
expose the deployability gap.

The best per-speaker-structure detector (at its 90%-specificity operating point) is
OR-combined with the RQ13 language-id entropy detector (threshold 0.409 bits) and the
combined sensitivity / specificity is measured on all 77 tracks.

Hypotheses
----------
- H22a: a per-speaker-structure detector achieves > 50% sensitivity on Mode S tracks
  (n=2) at > 90% specificity on non-hallucinated tracks (n=40).
  Kill: sensitivity <= 0% at 90% specificity.
- H22b: combining the best per-speaker-structure detector with lang-id entropy
  (threshold 0.409 bits) achieves > 95% sensitivity on all 37 hallucinated tracks.
  Kill: combined sensitivity <= 94.6% (lang-id alone).
- H22c: Mode S tracks have a distinct per-speaker-structure profile (permutation
  p < 0.05 on >= 1 feature). Kill: all features p >= 0.05.

This script is pure reanalysis (numpy + stdlib only; scipy / sklearn / Whisper are
NOT required). The surface-detector primitives (``script_category``,
``language_id_entropy``, ``compression_ratio``) are lifted verbatim from RQ13/RQ16/
RQ19 so the Mode S definition is directly comparable.
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
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "separator_failure_detector"
OUT_CSV = OUT_DIR / "separator_failure_results.csv"
OUT_JSON = OUT_DIR / "separator_failure_results.json"

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

    Matches ``whisper.audio.compression_ratio`` and RQ12/RQ13/RQ16/RQ19. Returns 0.0
    for empty/whitespace text. High CR (>~2.4) = repetitive loop."""
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


def nonempty_speaker_texts(window: dict[str, Any]) -> list[str]:
    """Return the list of stripped non-empty per-speaker separated texts."""
    return [
        str(t).strip()
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]


# ----------------------------------------------------- per-speaker-structure features
def per_speaker_length_entropy(window: dict[str, Any]) -> float:
    """Shannon entropy (bits) over the normalised per-speaker separated text lengths.

    Low = one speaker dominates. With a single non-empty speaker the entropy is 0
    (degenerate distribution)."""
    texts = nonempty_speaker_texts(window)
    lengths = [float(len(t)) for t in texts if len(t) > 0]
    total = sum(lengths)
    if total <= 0 or len(lengths) <= 1:
        return 0.0
    h = 0.0
    for L in lengths:
        p = L / total
        if p > 0:
            h -= p * math.log2(p)
    return h


def per_speaker_length_gini(window: dict[str, Any]) -> float:
    """Gini coefficient of the per-speaker separated text lengths.

    0 = perfectly equal split, 1 = maximally unequal (one speaker carries everything
    and at least one other has zero). With a single non-empty speaker the Gini is 0
    (no inequality to measure against). For [L, 0] it is 1.0."""
    texts = nonempty_speaker_texts(window)
    lengths = [float(len(t)) for t in texts if len(t) > 0]
    n = len(lengths)
    if n == 0:
        return 0.0
    # Include empty-channel speakers too: they are the zeros that drive Gini to 1.
    all_lengths = [float(len(str(t).strip())) for t in window.get("separated_text_per_speaker", {}).values()]
    all_lengths = [L for L in all_lengths if L >= 0]
    n_all = len(all_lengths)
    if n_all <= 1:
        return 0.0
    mean = sum(all_lengths) / n_all
    if mean <= 0:
        return 0.0
    s = 0.0
    for a in all_lengths:
        for b in all_lengths:
            s += abs(a - b)
    return s / (2.0 * n_all * mean)


def sep_to_mix_length_ratio(window: dict[str, Any]) -> float:
    """separated_total_length / mixed_text_length. Mode S hypothesis: approx 1.02."""
    sep = float(window.get("separated_total_length", 0) or 0)
    mix = float(window.get("mixed_text_length", 0) or 0)
    return sep / max(1.0, mix)


def sep_to_mix_runtime_ratio(window: dict[str, Any]) -> float:
    """separated_runtime_sec / mixed_runtime_sec."""
    sep = float(window.get("separated_runtime_sec", 0) or 0)
    mix = float(window.get("mixed_runtime_sec", 0) or 0)
    return sep / max(1e-6, mix)


def speaker_attribution_consistency(window: dict[str, Any]) -> float:
    """Fraction of non-empty per-speaker separated texts that appear as a contiguous
    substring of the mixed text (whitespace stripped on both sides).

    High = the separator faithfully preserved a contiguous span of mixed in each
    speaker channel; low = the separator re-decoded or re-ordered the audio. With no
    non-empty speakers the fraction is 0."""
    texts = nonempty_speaker_texts(window)
    if not texts:
        return 0.0
    mix = "".join(str(window.get("mixed_text", "") or "").split())
    if not mix:
        return 0.0
    hits = 0
    for t in texts:
        s = "".join(t.split())
        if s and s in mix:
            hits += 1
    return hits / len(texts)


def per_speaker_overlap_fraction(window: dict[str, Any]) -> float:
    """Fraction of non-empty speaker pairs whose separated texts share at least one
    non-whitespace character. 0 when there are fewer than 2 non-empty speakers."""
    texts = nonempty_speaker_texts(window)
    char_sets = [{c for c in t if not c.isspace()} for t in texts]
    n = len(char_sets)
    if n < 2:
        return 0.0
    pairs = 0
    shared = 0
    for i in range(n):
        for j in range(i + 1, n):
            pairs += 1
            if char_sets[i] & char_sets[j]:
                shared += 1
    return shared / pairs if pairs > 0 else 0.0


def effective_speaker_count(window: dict[str, Any]) -> float:
    """Number of distinct non-empty per-speaker separated texts (float for calibration)."""
    texts = nonempty_speaker_texts(window)
    return float(len(texts))


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
    """Bootstrap 95% CI for sensitivity = P(flag | label==1) with FIXED threshold.

    A ``direction`` of ``"none"`` means no threshold met the 90%-specificity target,
    so no track is ever flagged: sensitivity is 0 by definition and the CI is [0, 0].
    """
    if direction == "none":
        return 0.0, 0.0
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
    """Bootstrap 95% CI for specificity = P(not flag | label==0) with FIXED threshold.

    A ``direction`` of ``"none"`` means no track is ever flagged: specificity is 1
    by definition and the CI is [1, 1].
    """
    if direction == "none":
        return 1.0, 1.0
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
    """Permutation test for a distinct Mode S per-speaker-structure profile.

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

    # --- per-window surface features + labels + per-speaker-structure features
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

        # seven per-speaker-structure features
        ps_len_ent = per_speaker_length_entropy(w)
        ps_len_gini = per_speaker_length_gini(w)
        s2m_len = sep_to_mix_length_ratio(w)
        s2m_rt = sep_to_mix_runtime_ratio(w)
        sac = speaker_attribution_consistency(w)
        ps_overlap = per_speaker_overlap_fraction(w)
        eff_spk = effective_speaker_count(w)

        rows.append({
            "window_id": w["window_id"],
            "always_separated_cpwer": round(sep_cpwer, 6),
            "always_mixed_cpwer": round(mixed_cpwer, 6),
            "hallucinated": bool(halluc),
            "mode_s": bool(mode_s),
            "lang_id_entropy": round(ent, 6),
            "length_ratio": round(lr, 6),
            "cr": round(mcr, 6),
            "per_speaker_length_entropy": round(ps_len_ent, 6),
            "per_speaker_length_gini": round(ps_len_gini, 6),
            "sep_to_mix_length_ratio": round(s2m_len, 6),
            "sep_to_mix_runtime_ratio": round(s2m_rt, 6),
            "speaker_attribution_consistency": round(sac, 6),
            "per_speaker_overlap_fraction": round(ps_overlap, 6),
            "effective_speaker_count": round(eff_spk, 6),
            "num_speakers": w["num_speakers"],
            "_window": w,
        })

    n_halluc = sum(1 for r in rows if r["hallucinated"])
    n_nonhalluc = n - n_halluc
    n_mode_s = sum(1 for r in rows if r["mode_s"])
    mode_s_ids = [r["window_id"] for r in rows if r["mode_s"]]

    # --- calibrate each per-speaker-structure feature two-sidedly + permutation test
    feat_specs = [
        ("per_speaker_length_entropy", "per_speaker_length_entropy", "H22a",
         "Shannon entropy over normalised per-speaker separated text lengths"),
        ("per_speaker_length_gini", "per_speaker_length_gini", None,
         "Gini coefficient of per-speaker separated text lengths (incl. empty channels)"),
        ("sep_to_mix_length_ratio", "sep_to_mix_length_ratio", None,
         "separated_total_length / mixed_text_length (Mode S hypothesis: approx 1.02)"),
        ("sep_to_mix_runtime_ratio", "sep_to_mix_runtime_ratio", None,
         "separated_runtime_sec / mixed_runtime_sec"),
        ("speaker_attribution_consistency", "speaker_attribution_consistency", None,
         "fraction of non-empty speakers whose text is a contiguous substring of mixed"),
        ("per_speaker_overlap_fraction", "per_speaker_overlap_fraction", None,
         "fraction of non-empty speaker pairs sharing at least one character"),
        ("effective_speaker_count", "effective_speaker_count", None,
         "number of distinct non-empty per-speaker separated texts"),
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

    # --- best per-speaker-structure detector: most distinct profile (lowest perm p),
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

    # --- combined detector: best per-speaker-structure (90% spec op point) OR lang-id > 0.409
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
    h22a_supported = best["sensitivity_mode_s"] > 0.5 and best["specificity"] > 0.9
    h22a_killed = best["sensitivity_mode_s"] <= 0.0  # kill: sens <= 0% at 90% spec
    h22b_supported = comb_sens_ah > 0.95
    h22b_killed = comb_sens_ah <= 0.946  # kill: combined sens <= 94.6% (lang-id alone)
    h22c_supported = best["permutation_test"]["p_value_two_sided"] < 0.05
    h22c_killed = all(d["permutation_test"]["p_value_two_sided"] >= 0.05 for d in detector_results)

    # how many features have distinct profiles (perm p < 0.05)
    n_features_distinct = sum(1 for d in detector_results
                              if d["permutation_test"]["p_value_two_sided"] < 0.05)
    distinct_features = [d["detector"] for d in detector_results
                         if d["permutation_test"]["p_value_two_sided"] < 0.05]

    # Mode S per-feature profile (for FINDINGS)
    mode_s_profile = {}
    for d in detector_results:
        mode_s_profile[d["detector"]] = {
            "mode_s_mean": d["permutation_test"]["mode_s_mean"],
            "others_mean": d["permutation_test"]["others_mean"],
            "test_statistic": d["permutation_test"]["test_statistic"],
            "p_value": d["permutation_test"]["p_value_two_sided"],
        }

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ22: separator-failure detector — per-speaker transcript structure for Mode S residual",
        "closes_issue": 920,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "method": (
            "reanalysis only (no Whisper / no ASR run); seven per-speaker-structure "
            "features computed from separated_text_per_speaker and the mixed-track "
            "metadata. Each feature calibrated two-sidedly at >= 90% specificity on the "
            "40 non-hallucinated tracks. Best detector = lowest permutation p-value "
            "(most distinct Mode S profile). Combined = best per-speaker-structure "
            "(at 90% spec) OR lang-id entropy (threshold 0.409)."
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
            "rq19_finding": (
                "RQ19 (PR #919) found Mode S is a near-duplicate of the mixed transcript "
                "(separator failed, Whisper re-decoded the mixed audio). Content-similarity "
                "between sep-concatenated and mix CANNOT discriminate Mode S from clean "
                "single-speaker tracks (structural confound). RQ19 limitation #5 suggested "
                "per-speaker structure might break the confound."
            ),
            "mode_s_mechanism": (
                "Mode S separated text is concentrated in ONE speaker channel (the other "
                "channels are empty or near-empty) and is a near-duplicate of the mixed "
                "transcript. Window 22: num_speakers=2 but only 005-F carries text (98 chars, "
                "near-duplicate of the 96-char mixed). Window 30: num_speakers=1, 005-F "
                "carries 154 chars (near-duplicate of the 150-char mixed)."
            ),
        },
        "thresholds": {
            "lang_id_entropy": LANG_ID_ENTROPY_THRESHOLD,
            "length_ratio": LENGTH_RATIO_THRESHOLD,
            "cr": CR_THRESHOLD,
            "target_specificity": TARGET_SPECIFICITY,
        },
        "detectors": detector_results,
        "mode_s_per_feature_profile": mode_s_profile,
        "best_per_speaker_structure_detector": {
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
                "Reports the deployability gap for per-speaker-structure."
            ),
        },
        "lang_id_entropy_alone_reference": {
            "threshold": LANG_ID_ENTROPY_THRESHOLD,
            "specificity": round(lang_spec, 6),
            "sensitivity_all_hallucinated": round(lang_sens_ah, 6),
            "sensitivity_mode_s": round(lang_sens_ms, 6),
            "tp_all_hallucinated": tp_lang_ah, "fp": fp_lang,
            "note": "RQ13 lang-id entropy detector (no per-speaker-structure). By definition Mode S escapes it (lang-id < 0.409), so lang-id alone misses both Mode S tracks.",
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
                "Combined = best per-speaker-structure detector (at its 90%-specificity "
                "operating point) OR lang-id entropy. If per-speaker-structure catches any "
                "Mode S track the combined sensitivity rises above lang-id alone (94.6%)."
            ),
        },
        "hypothesis_verdicts": {
            "H22a": {
                "statement": "a per-speaker-structure detector achieves > 50% sensitivity on Mode S tracks (n=2) at > 90% specificity on non-hallucinated tracks (n=40)",
                "kill_criterion": "sensitivity <= 0% at 90% specificity",
                "best_detector": best_detector_name,
                "sensitivity_mode_s": best["sensitivity_mode_s"],
                "specificity": best["specificity"],
                "bootstrap_ci_95_mode_s_sensitivity": best["sensitivity_mode_s_ci_95"],
                "ceiling_analysis": best["ceiling_analysis"],
                "supported": bool(h22a_supported),
                "killed": bool(h22a_killed),
                "reason": (
                    f"At >= 90% specificity the best per-speaker-structure detector "
                    f"({best_detector_name}) catches {best['sensitivity_mode_s']:.0%} of Mode S. "
                    f"Ceiling analysis reports the max sensitivity achievable as the "
                    f"specificity floor is relaxed."
                ),
            },
            "H22b": {
                "statement": "combining the best per-speaker-structure detector with lang-id entropy (threshold 0.409 bits) achieves > 95% sensitivity on all 37 hallucinated tracks",
                "kill_criterion": "combined sensitivity <= 94.6% (lang-id alone)",
                "combined_sensitivity_all_hallucinated": round(comb_sens_ah, 6),
                "combined_specificity": round(comb_spec, 6),
                "bootstrap_ci_95_sensitivity": comb_sens_ci,
                "lang_id_alone_sensitivity": round(lang_sens_ah, 6),
                "supported": bool(h22b_supported),
                "killed": bool(h22b_killed),
                "reason": (
                    f"Combined sensitivity is {comb_sens_ah:.1%} ({tp_comb_ah}/{n_halluc}); "
                    f"lang-id alone is {lang_sens_ah:.1%} ({tp_lang_ah}/{n_halluc}). "
                    f"Per-speaker-structure adds {tp_comb_ah - tp_lang_ah} hallucinated "
                    f"tracks over lang-id alone ({tp_comb_ms} of {n_mode_s} Mode S)."
                ),
            },
            "H22c": {
                "statement": "Mode S tracks have a distinct per-speaker-structure profile (permutation p < 0.05 on >= 1 feature)",
                "kill_criterion": "all features p >= 0.05",
                "best_feature": best_key,
                "test_statistic": best["permutation_test"]["test_statistic"],
                "mode_s_mean": best["permutation_test"]["mode_s_mean"],
                "others_mean": best["permutation_test"]["others_mean"],
                "p_value_two_sided": best["permutation_test"]["p_value_two_sided"],
                "n_extreme": best["permutation_test"]["n_extreme"],
                "n_features_with_p_lt_0p05": n_features_distinct,
                "n_features_total": len(detector_results),
                "distinct_features": distinct_features,
                "all_features_p_values": {
                    d["detector"]: d["permutation_test"]["p_value_two_sided"]
                    for d in detector_results
                },
                "supported": bool(h22c_supported),
                "killed": bool(h22c_killed),
                "reason": (
                    f"Best feature {best_key} permutation p="
                    f"{best['permutation_test']['p_value_two_sided']:.4f} "
                    f"({best['permutation_test']['n_extreme']}/{N_PERM} extreme). "
                    f"{n_features_distinct} of {len(detector_results)} features have p < 0.05."
                ),
            },
        },
    }

    # --- write CSV (per-window)
    csv_fields = [
        "window_id", "hallucinated", "mode_s",
        "lang_id_entropy", "length_ratio", "cr",
        "per_speaker_length_entropy", "per_speaker_length_gini",
        "sep_to_mix_length_ratio", "sep_to_mix_runtime_ratio",
        "speaker_attribution_consistency", "per_speaker_overlap_fraction",
        "effective_speaker_count",
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
    print(f"=== RQ22: separator-failure detector (AISHELL-4, {n} tracks) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Hallucinated: {n_halluc}  |  non-hallucinated: {n_nonhalluc}  |  Mode S: {n_mode_s}")
    print(f"Mode S window ids: {mode_s_ids}")
    print(f"Target specificity: {TARGET_SPECIFICITY:.0%}  |  calibration: two-sided")
    print()
    print(f"{'detector':32s} {'dir':>5s} {'thresh':>9s} {'spec':>6s} {'sens_MS':>8s} {'sens_AH':>8s} {'perm_p':>8s}")
    for d in detector_results:
        print(f"{d['detector']:32s} {d['direction']:>5s} {d['threshold']:9.4f} "
              f"{d['specificity']:6.1%} {d['sensitivity_mode_s']:8.1%} "
              f"{d['sensitivity_all_hallucinated']:8.1%} "
              f"{d['permutation_test']['p_value_two_sided']:8.4f}")
    print()
    print(f"Best per-speaker-structure detector: {best_detector_name} "
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
    print(f"  H22a (per-speaker-structure sens_MS > 50% at spec > 90%): "
          f"{'SUPPORTED' if h22a_supported else 'NOT SUPPORTED'}"
          f"{' [KILLED]' if h22a_killed else ''} "
          f"(sens_MS={best['sensitivity_mode_s']:.1%}, spec={best['specificity']:.1%})")
    print(f"  H22b (combined sens_AH > 95%): "
          f"{'SUPPORTED' if h22b_supported else 'NOT SUPPORTED'}"
          f"{' [KILLED]' if h22b_killed else ''} "
          f"(sens_AH={comb_sens_ah:.1%}, spec={comb_spec:.1%})")
    print(f"  H22c (Mode S distinct profile, perm p < 0.05): "
          f"{'SUPPORTED' if h22c_supported else 'NOT SUPPORTED'}"
          f"{' [KILLED]' if h22c_killed else ''} "
          f"(p={best['permutation_test']['p_value_two_sided']:.4f}, "
          f"{n_features_distinct}/{len(detector_results)} features p<0.05)")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
