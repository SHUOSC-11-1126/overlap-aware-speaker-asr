#!/usr/bin/env python3
"""RQ70: Per-Mode BCa CI Decomposition of the Corrected Router.

RQ55 (PR #979) and RQ58 (PR #981) both found the corrected router's BCa CI
*includes* the oracle -- "reaches oracle within noise." But the 77 AISHELL-4
windows are heterogeneous. RQ14 (PR #905) decomposed the 37 hallucinated
separated tracks into a five-mode taxonomy, and RQ19 (PR #916) isolated the
2 "Mode S" windows (22, 30) -- the monoscript-Chinese hallucinations that
escape every surface detector (lang-id entropy < 0.409, length ratio < 2.0,
CR < 2.4). RQ70 asks: **does the BCa CI exclude the oracle for some
hallucination modes but not others?** This would reveal whether the "within
noise" verdict is uniform or driven by a specific mode.

Three-way mutually-exclusive decomposition (per RQ14/RQ16/RQ19):

  - **Mode S** (n=2): hallucinated AND lang_id_entropy < 0.409 AND
    length_ratio < 2.0 AND cr < 2.4 -- the residual that escapes surface
    detection (windows 22, 30, per RQ19).
  - **Diverse hallucination** (n=35): hallucinated AND NOT Mode S -- the
    "diverse" hallucinations the lang-id entropy detector catches (RQ12/RQ14's
    37 hallucinated tracks minus the 2 Mode S tracks).
  - **Non-hallucinated** (n=40): always_separated_cpwer <= 1.0.

(Note: the task spec listed the split as "Mode S (2), Diverse hallucination
(37), Non-hallucinated (38)". The *data-driven* mutually-exclusive split per
RQ12/RQ14/RQ19 is (2, 35, 40) = 77: RQ12/RQ14's "37 hallucinated" *includes*
the 2 Mode S tracks, so Diverse-hallucination-minus-Mode-S = 35, and
non-hallucinated = 40. We use the data-driven split throughout and document
the discrepancy transparently in FINDINGS.md.)

Pre-registered Hypotheses (KILL criteria)
-----------------------------------------
- **H70a**: Non-Mode-S windows BCa CI excludes oracle. **KILL if includes
  oracle.** (Sensitivity: drop the 2 Mode S windows, recompute BCa CI on the
  remaining 75 -- does the narrower CI now exclude the oracle?)
- **H70b**: Mode S windows BCa CI includes oracle (Mode S is the noise source).
  **KILL if excludes oracle.** (Caveat: n=2 is too small for stable BCa -- the
  CI is reported but flagged as unstable.)
- **H70c**: Per-mode CI widths differ by > 50% (max/min ratio > 1.5).
  **KILL if <= 1.5.**

Method
------
For each of the 77 AISHELL-4 windows we:
  1. Compute the corrected router's per-window cpWER at both word-level
     (stored) and char-level (recomputed via MeetEval 0.4.3 cpwer/orcwer with
     char-level tokenisation, RQ31 convention) -- lifted verbatim from RQ55.
  2. Classify each window into Mode S / Diverse hallucination / Non-hallucinated
     per RQ14/RQ19 (Mode S definition: hallucinated AND lang_id_entropy <
     0.409 AND length_ratio < 2.0 AND cr < 2.4).
  3. For each mode subset AND for the "Non-Mode-S" sensitivity subset (75
     windows), compute the BCa CI (B=10,000, seed=42, jackknife acceleration)
     on the corrected router cpWER -- bootstrap/BCa helpers lifted verbatim
     from RQ39/RQ55.
  4. Compare each CI to the oracle (subset oracle mean for the per-mode
     comparison; global oracle for context). Compute width ratio (max/min)
     across modes for H70c.

Reanalysis only -- no Whisper / no ASR runs / no LLM. Uses the stored
transcripts in results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json.

Label: experimental/frontier. Closes #998.

Run:
    /opt/homebrew/bin/python3 results/frontier/per_mode_bca_decomposition/analysis.py
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
from scipy.stats import norm

try:
    import meeteval
    from meeteval.wer import cpwer, orcwer
except ImportError:  # pure helpers can still be tested without MeetEval
    meeteval = None
    cpwer = None
    orcwer = None

# --------------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_DIR = Path(__file__).resolve().parent
OUT_CSV = OUT_DIR / "per_mode_bca_results.csv"
OUT_JSON = OUT_DIR / "per_mode_bca_results.json"

# ------------------------------------------------------------------ thresholds
LANG_ID_ENTROPY_THRESHOLD = 0.38
MODE_S_LANG_ENTROPY = 0.409
MODE_S_LENGTH_RATIO = 2.0
MODE_S_CR = 2.4
CATASTROPHIC_CPWER = 1.0
N_BOOT = 10000
SEED = 42
ALPHA = 0.05
SESSION_ID = "s1"
EPS = 1e-9

# RQ55 char-level reference values (for reproducibility checks).
RQ55_CHAR_BCA_CI = (0.873026, 0.931406)
RQ55_CHAR_CORRECTED = 0.906097
RQ55_CHAR_ORACLE = 0.8768
RQ55_WORD_BCA_CI = (1.012987, 1.097403)
RQ55_WORD_CORRECTED = 1.0433
RQ55_WORD_ORACLE = 1.0173


# ===========================================================================
# Part 1: detector primitives (lifted VERBATIM from RQ13/RQ16/RQ55)
# ===========================================================================

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
    """Shannon entropy (bits) over the script-category distribution (RQ13)."""
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


def max_across_speakers(window: dict[str, Any], fn: Callable[[str], float]) -> float:
    """Max of fn(text) over the per-speaker separated transcripts (worst-case)."""
    vals = [
        fn(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


def corrected_router_decision(window: dict[str, Any]) -> str:
    """RQ55 corrected-router decision using lang-id entropy alone (threshold 0.38)."""
    ent = max_across_speakers(window, language_id_entropy)
    return "mixed" if ent > LANG_ID_ENTROPY_THRESHOLD else "separated"


# ===========================================================================
# Part 1b: Mode S classification primitives (lifted from RQ12/RQ14/RQ19)
# ===========================================================================

def compression_ratio(text: str) -> float:
    """Whisper-style compression ratio: len(utf8 bytes) / len(zlib-compressed)."""
    if not text or not text.strip():
        return 0.0
    b = text.encode("utf-8")
    c = zlib.compress(b)
    return len(b) / len(c) if len(c) > 0 else 0.0


def max_cr_across_speakers(window: dict[str, Any]) -> float:
    """Max Whisper-style CR over per-speaker separated transcripts (RQ12/RQ14)."""
    vals = [
        compression_ratio(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


def separated_total_length(window: dict[str, Any]) -> int:
    """Total non-whitespace char length across per-speaker separated transcripts."""
    total = 0
    for t in window.get("separated_text_per_speaker", {}).values():
        if t is not None:
            total += len(str(t).replace(" ", "").replace("\n", "").replace("\t", ""))
    return total


def mixed_text_length(window: dict[str, Any]) -> int:
    """Non-whitespace char length of the mixed transcript."""
    txt = window.get("mixed_text", "") or ""
    return len(txt.replace(" ", "").replace("\n", "").replace("\t", ""))


def length_ratio(window: dict[str, Any]) -> float:
    """separated_total_length / max(mixed_text_length, 1) (RQ14)."""
    mlen = mixed_text_length(window)
    slen = separated_total_length(window)
    return slen / max(mlen, 1)


def is_hallucinated(window: dict[str, Any]) -> bool:
    """RQ12 hallucination criterion: always_separated_cpwer > 1.0."""
    return float(window["always_separated_cpwer"]) > CATASTROPHIC_CPWER


def is_mode_s(window: dict[str, Any]) -> bool:
    """RQ19 Mode S: hallucinated AND lang_id_entropy < 0.409 AND
    length_ratio < 2.0 AND cr < 2.4.

    Verified to be exactly windows 22 and 30, matching RQ16/RQ19's residual."""
    if not is_hallucinated(window):
        return False
    ent = max_across_speakers(window, language_id_entropy)
    lr = length_ratio(window)
    cr = max_cr_across_speakers(window)
    return (ent < MODE_S_LANG_ENTROPY
            and lr < MODE_S_LENGTH_RATIO
            and cr < MODE_S_CR)


def classify_mode(window: dict[str, Any]) -> str:
    """Three-way mutually-exclusive classification (RQ14/RQ16/RQ19)."""
    if is_mode_s(window):
        return "mode_s"
    if is_hallucinated(window):
        return "diverse_hallucination"
    return "non_hallucinated"


# ===========================================================================
# Part 2: MeetEval char-level helpers (lifted VERBATIM from RQ31/RQ55)
# ===========================================================================

def to_char_level(text: str) -> str:
    """Space-separate each character so MeetEval treats it as one 'word'."""
    return " ".join(list(text))


def build_segments(speaker_text: dict[str, str]) -> list[dict]:
    """Build MeetEval char-level segment dicts from {speaker: text}."""
    segs = []
    for spk, txt in speaker_text.items():
        if not txt or not txt.strip():
            continue
        segs.append({
            "session_id": SESSION_ID,
            "speaker": spk,
            "words": to_char_level(txt),
        })
    return segs


def build_mixed_segment(mixed_text: str) -> list[dict]:
    """Build a single-channel hypothesis segment for orcWER (char-level)."""
    if not mixed_text or not mixed_text.strip():
        return []
    return [{
        "session_id": SESSION_ID,
        "speaker": "mix",
        "words": to_char_level(mixed_text),
    }]


def safe_cpwer(ref_segs, hyp_segs) -> tuple[float, int, int]:
    """Run cpwer; on empty input return the project's empty-sentinel."""
    if not ref_segs or not hyp_segs:
        return 1.0, -1, -1
    r = cpwer(ref_segs, hyp_segs)[SESSION_ID]
    return float(r.error_rate), int(r.errors), int(r.length)


def safe_orcwer(ref_segs, hyp_segs) -> tuple[float, int, int]:
    """Run orcwer; on empty input return the project's empty-sentinel."""
    if not ref_segs or not hyp_segs:
        return 1.0, -1, -1
    r = orcwer(ref_segs, hyp_segs)[SESSION_ID]
    return float(r.error_rate), int(r.errors), int(r.length)


# ===========================================================================
# Part 3: bootstrap helpers (lifted VERBATIM from RQ39/RQ55)
# ===========================================================================

def bootstrap_indices(n: int, n_boot: int, seed: int) -> np.ndarray:
    """Return an ``(n_boot, n)`` int array of resample indices (with replacement)."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, n, size=(n_boot, n))


def bootstrap_distribution(values: np.ndarray, n_boot: int, seed: int) -> np.ndarray:
    """Return an ``n_boot`` array of bootstrap means of ``values``."""
    values = np.asarray(values, dtype=float)
    n = len(values)
    idx = bootstrap_indices(n, n_boot, seed)
    return values[idx].mean(axis=1)


def percentile_ci(boot_dist: np.ndarray, alpha: float = ALPHA) -> tuple[float, float]:
    """Percentile CI: 2.5 / 97.5 percentiles of the bootstrap distribution."""
    boot_dist = np.asarray(boot_dist, dtype=float)
    lo = float(np.percentile(boot_dist, 100.0 * (alpha / 2.0)))
    hi = float(np.percentile(boot_dist, 100.0 * (1.0 - alpha / 2.0)))
    return lo, hi


def _jackknife_means(values: np.ndarray) -> np.ndarray:
    """Leave-one-out jackknife means of ``values`` (length-``n`` array)."""
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n < 2:
        return np.array([float(values.mean())])
    total = float(values.sum())
    return (total - values) / (n - 1)


def bca_ci(
    values: np.ndarray, boot_dist: np.ndarray, alpha: float = ALPHA
) -> tuple[float, float]:
    """BCa (bias-corrected + accelerated) CI for the mean of ``values``."""
    values = np.asarray(values, dtype=float)
    boot_dist = np.asarray(boot_dist, dtype=float)
    n = len(values)
    if n < 2:
        theta = float(values.mean()) if n == 1 else float("nan")
        return theta, theta

    theta_hat = float(values.mean())

    prop_less = float(np.mean(boot_dist < theta_hat))
    eps_clip = 0.5 / len(boot_dist)
    prop_less = min(max(prop_less, eps_clip), 1.0 - eps_clip)
    z0 = float(norm.ppf(prop_less))

    jack = _jackknife_means(values)
    jack_mean = float(jack.mean())
    diff = jack_mean - jack
    num = float(np.sum(diff ** 3))
    den = 6.0 * (float(np.sum(diff ** 2)) ** 1.5)
    a = num / den if den > 0 else 0.0

    z_lo = float(norm.ppf(alpha / 2.0))
    z_hi = float(norm.ppf(1.0 - alpha / 2.0))

    denom_lo = 1.0 - a * (z0 + z_lo)
    denom_hi = 1.0 - a * (z0 + z_hi)
    if abs(denom_lo) < EPS or abs(denom_hi) < EPS:
        return percentile_ci(boot_dist, alpha)

    alpha1 = float(norm.cdf(z0 + (z0 + z_lo) / denom_lo))
    alpha2 = float(norm.cdf(z0 + (z0 + z_hi) / denom_hi))

    alpha1 = min(max(alpha1, 0.0), 1.0)
    alpha2 = min(max(alpha2, 0.0), 1.0)

    lo = float(np.percentile(boot_dist, 100.0 * alpha1))
    hi = float(np.percentile(boot_dist, 100.0 * alpha2))
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


# ===========================================================================
# Part 4: per-mode BCa CI driver
# ===========================================================================

def _round6(x: float) -> float:
    return round(float(x), 6)


def _ci_pair(ci: tuple[float, float]) -> list[float]:
    return [_round6(ci[0]), _round6(ci[1])]


def ci_includes(ci: tuple[float, float], point: float) -> bool:
    """True if point is within [ci_lo, ci_hi] (inclusive)."""
    return ci[0] <= point <= ci[1]


def ci_excludes(ci: tuple[float, float], point: float) -> bool:
    """True if point is strictly outside [ci_lo, ci_hi]."""
    return not ci_includes(ci, point)


def _compute_window_cpwer(w: dict[str, Any]) -> dict[str, Any]:
    """Compute per-window word-level + char-level cpWER for all four policies."""
    wid = w["window_id"]
    refs = w["ref_text_per_speaker"]
    sep_hyps = w["separated_text_per_speaker"]
    mixed = w.get("mixed_text", "")

    ent = max_across_speakers(w, language_id_entropy)
    decision = corrected_router_decision(w)

    word_mixed_cpwer = float(w["always_mixed_cpwer"])
    word_sep_cpwer = float(w["always_separated_cpwer"])
    word_oracle_cpwer = float(w["oracle_best_cpwer"])
    word_corrected_cpwer = word_mixed_cpwer if decision == "mixed" else word_sep_cpwer

    ref_segs = build_segments(refs)
    sep_segs = build_segments(sep_hyps)
    mix_segs = build_mixed_segment(mixed)

    separated_char, sep_err, sep_len = safe_cpwer(ref_segs, sep_segs)
    mixed_char, mix_err, mix_len = safe_orcwer(ref_segs, mix_segs)

    corrected_char = mixed_char if decision == "mixed" else separated_char
    oracle_char = min(mixed_char, separated_char)

    lr = length_ratio(w)
    cr = max_cr_across_speakers(w)
    hall = is_hallucinated(w)
    mode = classify_mode(w)

    return {
        "window_id": wid,
        "overlap_label": w["overlap_label"],
        "num_speakers": w["num_speakers"],
        "lang_id_entropy": round(ent, 6),
        "corrected_decision": decision,
        "hallucinated": bool(hall),
        "mode_s": bool(is_mode_s(w)),
        "mode": mode,
        "length_ratio": round(lr, 6),
        "max_cr": round(cr, 6),
        "word_mixed_cpwer": _round6(word_mixed_cpwer),
        "word_separated_cpwer": _round6(word_sep_cpwer),
        "word_oracle_cpwer": _round6(word_oracle_cpwer),
        "word_corrected_cpwer": _round6(word_corrected_cpwer),
        "char_mixed_cpwer": _round6(mixed_char),
        "char_separated_cpwer": _round6(separated_char),
        "char_oracle_cpwer": _round6(oracle_char),
        "char_corrected_cpwer": _round6(corrected_char),
        "separated_char_errors": sep_err,
        "separated_char_length": sep_len,
        "mixed_char_errors": mix_err,
        "mixed_char_length": mix_len,
    }


def _subset_bca(values: np.ndarray, label: str) -> dict[str, Any]:
    """Compute percentile + BCa CI for a subset of cpWER values."""
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n == 0:
        return {
            "label": label, "n": 0, "mean": float("nan"),
            "percentile_ci": [float("nan"), float("nan")],
            "bca_ci": [float("nan"), float("nan")],
            "bca_width": float("nan"),
            "stable": False, "stability_note": "n=0",
        }
    mean = float(values.mean())
    if n == 1:
        return {
            "label": label, "n": 1, "mean": mean,
            "percentile_ci": [mean, mean],
            "bca_ci": [mean, mean],
            "bca_width": 0.0,
            "stable": False, "stability_note": "n=1 (degenerate; no variance)",
        }
    boot = bootstrap_distribution(values, N_BOOT, SEED)
    pct_ci = percentile_ci(boot)
    bca = bca_ci(values, boot)
    width = bca[1] - bca[0]
    stable = n >= 5
    note = "stable" if stable else (
        f"n={n} too small for stable BCa; CI reported but flagged as unstable"
    )
    return {
        "label": label, "n": n, "mean": _round6(mean),
        "percentile_ci": _ci_pair(pct_ci),
        "bca_ci": _ci_pair(bca),
        "bca_width": _round6(width),
        "stable": bool(stable), "stability_note": note,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]
    n_total = len(windows)

    rows = [_compute_window_cpwer(w) for w in windows]

    mode_s_idx = [i for i, r in enumerate(rows) if r["mode"] == "mode_s"]
    diverse_idx = [i for i, r in enumerate(rows) if r["mode"] == "diverse_hallucination"]
    nonhall_idx = [i for i, r in enumerate(rows) if r["mode"] == "non_hallucinated"]
    nonmodes_idx = [i for i, r in enumerate(rows) if r["mode"] != "mode_s"]
    all_idx = list(range(n_total))

    mode_counts = {
        "mode_s": len(mode_s_idx),
        "diverse_hallucination": len(diverse_idx),
        "non_hallucinated": len(nonhall_idx),
        "non_mode_s": len(nonmodes_idx),
        "all": n_total,
    }
    mode_s_window_ids = [rows[i]["window_id"] for i in mode_s_idx]

    def _arr(idx_list: list[int], key: str) -> np.ndarray:
        return np.array([rows[i][key] for i in idx_list], dtype=float)

    subsets = {
        "all": all_idx,
        "mode_s": mode_s_idx,
        "diverse_hallucination": diverse_idx,
        "non_hallucinated": nonhall_idx,
        "non_mode_s": nonmodes_idx,
    }

    per_subset: dict[str, dict[str, Any]] = {}
    for sname, sidx in subsets.items():
        word_corr = _arr(sidx, "word_corrected_cpwer")
        char_corr = _arr(sidx, "char_corrected_cpwer")
        word_oracle = _arr(sidx, "word_oracle_cpwer")
        char_oracle = _arr(sidx, "char_oracle_cpwer")

        word_bca = _subset_bca(word_corr, f"{sname}/word")
        char_bca = _subset_bca(char_corr, f"{sname}/char")

        per_subset[sname] = {
            "n": len(sidx),
            "word_corrected_mean": _round6(float(word_corr.mean())) if len(word_corr) else float("nan"),
            "char_corrected_mean": _round6(float(char_corr.mean())) if len(char_corr) else float("nan"),
            "word_oracle_mean": _round6(float(word_oracle.mean())) if len(word_oracle) else float("nan"),
            "char_oracle_mean": _round6(float(char_oracle.mean())) if len(char_oracle) else float("nan"),
            "word_percentile_ci": word_bca["percentile_ci"],
            "word_bca_ci": word_bca["bca_ci"],
            "word_bca_width": word_bca["bca_width"],
            "char_percentile_ci": char_bca["percentile_ci"],
            "char_bca_ci": char_bca["bca_ci"],
            "char_bca_width": char_bca["bca_width"],
            "stable": bool(word_bca["stable"] and char_bca["stable"]),
            "stability_note": word_bca["stability_note"] if not word_bca["stable"] else char_bca["stability_note"],
        }

    global_word_oracle = float(_arr(all_idx, "word_oracle_cpwer").mean())
    global_char_oracle = float(_arr(all_idx, "char_oracle_cpwer").mean())

    # H70a: Non-Mode-S
    nm_word_bca = tuple(per_subset["non_mode_s"]["word_bca_ci"])
    nm_char_bca = tuple(per_subset["non_mode_s"]["char_bca_ci"])
    nm_word_oracle = per_subset["non_mode_s"]["word_oracle_mean"]
    nm_char_oracle = per_subset["non_mode_s"]["char_oracle_mean"]

    h70a_word_excludes = ci_excludes(nm_word_bca, nm_word_oracle)
    h70a_char_excludes = ci_excludes(nm_char_bca, nm_char_oracle)
    h70a_word_lower_above_oracle = nm_word_bca[0] > nm_word_oracle
    h70a_char_lower_above_oracle = nm_char_bca[0] > nm_char_oracle
    h70a_supported = (
        ci_excludes(nm_word_bca, nm_word_oracle)
        and ci_excludes(nm_char_bca, nm_char_oracle)
    )

    # H70b: Mode S
    ms_word_bca = tuple(per_subset["mode_s"]["word_bca_ci"])
    ms_char_bca = tuple(per_subset["mode_s"]["char_bca_ci"])
    ms_word_oracle = per_subset["mode_s"]["word_oracle_mean"]
    ms_char_oracle = per_subset["mode_s"]["char_oracle_mean"]

    h70b_word_includes = ci_includes(ms_word_bca, ms_word_oracle)
    h70b_char_includes = ci_includes(ms_char_bca, ms_char_oracle)
    h70b_supported = (
        ci_includes(ms_word_bca, ms_word_oracle)
        and ci_includes(ms_char_bca, ms_char_oracle)
    )
    h70b_stable = per_subset["mode_s"]["stable"]

    # H70c: width ratio
    widths_char = {
        "mode_s": per_subset["mode_s"]["char_bca_width"],
        "diverse_hallucination": per_subset["diverse_hallucination"]["char_bca_width"],
        "non_hallucinated": per_subset["non_hallucinated"]["char_bca_width"],
    }
    widths_word = {
        "mode_s": per_subset["mode_s"]["word_bca_width"],
        "diverse_hallucination": per_subset["diverse_hallucination"]["word_bca_width"],
        "non_hallucinated": per_subset["non_hallucinated"]["word_bca_width"],
    }

    def _width_ratio(widths: dict[str, float]) -> tuple[float, float, float, str, str]:
        vals = {k: v for k, v in widths.items() if not math.isnan(v) and v > 0}
        if not vals:
            return float("nan"), float("nan"), float("nan"), "", ""
        wmin = min(vals.values())
        wmax = max(vals.values())
        ratio = wmax / wmin if wmin > 0 else float("nan")
        kmin = min(vals, key=vals.get)
        kmax = max(vals, key=vals.get)
        return ratio, wmin, wmax, kmin, kmax

    char_ratio, char_wmin, char_wmax, char_kmin, char_kmax = _width_ratio(widths_char)
    word_ratio, word_wmin, word_wmax, word_kmin, word_kmax = _width_ratio(widths_word)

    # Also compute the stable-only ratio (Diverse vs Non-hallucinated).
    stable_char_widths = {
        "diverse_hallucination": widths_char["diverse_hallucination"],
        "non_hallucinated": widths_char["non_hallucinated"],
    }
    stable_word_widths = {
        "diverse_hallucination": widths_word["diverse_hallucination"],
        "non_hallucinated": widths_word["non_hallucinated"],
    }
    stable_char_ratio, _, _, stable_char_kmin, stable_char_kmax = _width_ratio(stable_char_widths)
    stable_word_ratio, _, _, stable_word_kmin, stable_word_kmax = _width_ratio(stable_word_widths)

    h70c_supported = (char_ratio > 1.5) or (word_ratio > 1.5)

    # Reproducibility
    repro_word = per_subset["all"]["word_bca_ci"]
    repro_char = per_subset["all"]["char_bca_ci"]
    repro_word_ok = (
        abs(repro_word[0] - RQ55_WORD_BCA_CI[0]) < 1e-5
        and abs(repro_word[1] - RQ55_WORD_BCA_CI[1]) < 1e-5
    )
    repro_char_ok = (
        abs(repro_char[0] - RQ55_CHAR_BCA_CI[0]) < 1e-5
        and abs(repro_char[1] - RQ55_CHAR_BCA_CI[1]) < 1e-5
    )

    meeteval_version = meeteval.__version__ if meeteval is not None else None

    decision_counts = {
        "mixed": sum(1 for r in rows if r["corrected_decision"] == "mixed"),
        "separated": sum(1 for r in rows if r["corrected_decision"] == "separated"),
    }

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ70: Per-Mode BCa CI Decomposition of the Corrected Router",
        "closes_issue": 998,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "meeteval_version": meeteval_version,
        "meeting_id": data["meeting_id"],
        "n_windows": n_total,
        "method": (
            "Reanalysis only (no Whisper / no ASR / no LLM). RQ55 corrected "
            "router (lang-id entropy > 0.38 bits -> MIXED, else SEPARATED) "
            "applied at word-level (stored cpWER) and char-level (MeetEval "
            "0.4.3 cpwer/orcwer, RQ31 char tokenisation). Three-way mutually-"
            "exclusive mode classification per RQ14/RQ19: Mode S (hallucinated "
            "AND lang_id_entropy < 0.409 AND length_ratio < 2.0 AND cr < 2.4), "
            "Diverse hallucination (hallucinated AND NOT Mode S), Non-"
            "hallucinated (separated_cpwer <= 1.0). Bootstrap 10,000 resamples, "
            "seed=42, BCa CI (jackknife acceleration, RQ39/RQ55 verbatim). "
            "Detector/MeetEval/bootstrap helpers lifted verbatim from RQ55."
        ),
        "thresholds": {
            "lang_id_entropy_router": LANG_ID_ENTROPY_THRESHOLD,
            "mode_s_lang_entropy": MODE_S_LANG_ENTROPY,
            "mode_s_length_ratio": MODE_S_LENGTH_RATIO,
            "mode_s_cr": MODE_S_CR,
            "hallucination_cpwer": CATASTROPHIC_CPWER,
            "note": (
                "Router threshold 0.38 (RQ55) verified identical routing to "
                "RQ13's 0.409. Mode S definition from RQ19 (windows 22, 30)."
            ),
        },
        "bootstrap": {
            "n_boot": N_BOOT, "seed": SEED, "alpha": ALPHA,
            "convention": "rng.integers(0, n, size=n) per resample (RQ16/RQ39 verbatim)",
        },
        "mode_counts": mode_counts,
        "mode_s_window_ids": mode_s_window_ids,
        "mode_counts_note": (
            "Task spec listed (Mode S=2, Diverse=37, Non-hall=38). Data-driven "
            "mutually-exclusive split per RQ12/RQ14/RQ19 is (2, 35, 40)=77: "
            "RQ12/RQ14's '37 hallucinated' INCLUDES the 2 Mode S tracks, so "
            "Diverse-minus-Mode-S = 35, and non-hallucinated = 40. Reported "
            "transparently per HONESTY REQUIREMENT."
        ),
        "decision_counts": decision_counts,
        "global_oracle": {
            "word_level": _round6(global_word_oracle),
            "char_level": _round6(global_char_oracle),
            "note": "Mean oracle cpWER over all 77 windows (RQ55 reference).",
        },
        "per_subset": per_subset,
        "stable_only_width_ratio": {
            "char_ratio": _round6(stable_char_ratio),
            "char_min_mode": stable_char_kmin,
            "char_max_mode": stable_char_kmax,
            "word_ratio": _round6(stable_word_ratio),
            "word_min_mode": stable_word_kmin,
            "word_max_mode": stable_word_kmax,
            "note": "Width ratio computed over the two stable subsets (Diverse, Non-hallucinated) only.",
        },
        "reproducibility_check": {
            "all_word_bca_ci": repro_word,
            "rq55_word_bca_ci": [RQ55_WORD_BCA_CI[0], RQ55_WORD_BCA_CI[1]],
            "word_reproduces": bool(repro_word_ok),
            "all_char_bca_ci": repro_char,
            "rq55_char_bca_ci": [RQ55_CHAR_BCA_CI[0], RQ55_CHAR_BCA_CI[1]],
            "char_reproduces": bool(repro_char_ok),
        },
        "hypothesis_verdicts": {
            "H70a": {
                "statement": (
                    "Non-Mode-S windows BCa CI excludes oracle (drop Mode S, "
                    "the corrected router's BCa CI narrows below oracle)."
                ),
                "subset": "non_mode_s (n=75)",
                "word_bca_ci": _ci_pair(nm_word_bca),
                "word_oracle_subset": _round6(nm_word_oracle),
                "word_oracle_global": _round6(global_word_oracle),
                "word_excludes_oracle": bool(h70a_word_excludes),
                "word_lower_above_oracle": bool(h70a_word_lower_above_oracle),
                "char_bca_ci": _ci_pair(nm_char_bca),
                "char_oracle_subset": _round6(nm_char_oracle),
                "char_oracle_global": _round6(global_char_oracle),
                "char_excludes_oracle": bool(h70a_char_excludes),
                "char_lower_above_oracle": bool(h70a_char_lower_above_oracle),
                "success_criterion": "BCa CI excludes oracle at BOTH granularities",
                "kill_criterion": "BCa CI includes oracle at EITHER granularity",
                "supported": bool(h70a_supported),
            },
            "H70b": {
                "statement": (
                    "Mode S windows BCa CI includes oracle (Mode S is the noise "
                    "source keeping the global CI above oracle)."
                ),
                "subset": "mode_s (n=2)",
                "stability_caveat": (
                    "n=2 is too small for stable BCa (only C(2,2)=1 distinct "
                    "resample composition; jackknife acceleration degenerate). "
                    "CI reported but flagged as unstable per HONESTY REQUIREMENT."
                ),
                "word_bca_ci": _ci_pair(ms_word_bca),
                "word_oracle_subset": _round6(ms_word_oracle),
                "word_includes_oracle": bool(h70b_word_includes),
                "char_bca_ci": _ci_pair(ms_char_bca),
                "char_oracle_subset": _round6(ms_char_oracle),
                "char_includes_oracle": bool(h70b_char_includes),
                "success_criterion": "BCa CI includes oracle at BOTH granularities",
                "kill_criterion": "BCa CI excludes oracle at EITHER granularity",
                "supported": bool(h70b_supported),
                "stable": bool(h70b_stable),
            },
            "H70c": {
                "statement": (
                    "Per-mode BCa CI widths differ by > 50% (max/min ratio > 1.5)."
                ),
                "char_widths": widths_char,
                "char_width_ratio": _round6(char_ratio),
                "char_min_width": _round6(char_wmin),
                "char_max_width": _round6(char_wmax),
                "char_min_mode": char_kmin,
                "char_max_mode": char_kmax,
                "word_widths": widths_word,
                "word_width_ratio": _round6(word_ratio),
                "word_min_width": _round6(word_wmin),
                "word_max_width": _round6(word_wmax),
                "word_min_mode": word_kmin,
                "word_max_mode": word_kmax,
                "stable_only_char_ratio": _round6(stable_char_ratio),
                "stable_only_word_ratio": _round6(stable_word_ratio),
                "success_criterion": "max/min width ratio > 1.5 at EITHER granularity",
                "kill_criterion": "max/min width ratio <= 1.5 at BOTH granularities",
                "supported": bool(h70c_supported),
                "note": (
                    "Mode S width (n=2) is included in the ratio but flagged "
                    "as unstable; the ratio is dominated by the Mode S "
                    "degenerate width (often 0 or near-0), which can inflate "
                    "the ratio artificially. The stable-only ratio "
                    "(Diverse vs Non-hallucinated) is the more reliable comparison."
                ),
            },
        },
    }

    csv_fields = list(rows[0].keys())
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for r in rows:
            wr.writerow(r)

    summary_with_rows = dict(summary)
    summary_with_rows["per_window"] = rows
    OUT_JSON.write_text(
        json.dumps(summary_with_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"=== RQ70: Per-Mode BCa CI Decomposition ({n_total} windows) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"MeetEval: {meeteval_version}  |  Bootstrap: {N_BOOT} resamples, seed={SEED}")
    print()
    print("Mode counts (mutually exclusive, per RQ14/RQ19):")
    for k, v in mode_counts.items():
        print(f"  {k:24s}: {v}")
    print(f"  Mode S window ids: {mode_s_window_ids}")
    print()
    print("Per-subset BCa CI (corrected router cpWER):")
    for sname in ["all", "mode_s", "diverse_hallucination", "non_hallucinated", "non_mode_s"]:
        s = per_subset[sname]
        stable_tag = "" if s["stable"] else "  [UNSTABLE]"
        print(f"  {sname:24s} (n={s['n']}){stable_tag}")
        print(f"    word: corr={s['word_corrected_mean']:.4f} oracle={s['word_oracle_mean']:.4f} "
              f"BCa=[{s['word_bca_ci'][0]:.4f}, {s['word_bca_ci'][1]:.4f}] w={s['word_bca_width']:.4f}")
        print(f"    char: corr={s['char_corrected_mean']:.4f} oracle={s['char_oracle_mean']:.4f} "
              f"BCa=[{s['char_bca_ci'][0]:.4f}, {s['char_bca_ci'][1]:.4f}] w={s['char_bca_width']:.4f}")
    print()
    print("Reproducibility (all-77 vs RQ55):")
    print(f"  word BCa CI: {repro_word} vs RQ55 {list(RQ55_WORD_BCA_CI)} -> {'OK' if repro_word_ok else 'FAIL'}")
    print(f"  char BCa CI: {repro_char} vs RQ55 {list(RQ55_CHAR_BCA_CI)} -> {'OK' if repro_char_ok else 'FAIL'}")
    print()
    print("Hypothesis verdicts:")
    print(f"  H70a (Non-Mode-S BCa excludes oracle): "
          f"{'SUPPORTED' if h70a_supported else 'KILLED'}")
    print(f"    word: BCa=[{nm_word_bca[0]:.4f}, {nm_word_bca[1]:.4f}] vs oracle={nm_word_oracle:.4f} "
          f"-> excludes={h70a_word_excludes}, lower_above={h70a_word_lower_above_oracle}")
    print(f"    char: BCa=[{nm_char_bca[0]:.4f}, {nm_char_bca[1]:.4f}] vs oracle={nm_char_oracle:.4f} "
          f"-> excludes={h70a_char_excludes}, lower_above={h70a_char_lower_above_oracle}")
    print(f"  H70b (Mode S BCa includes oracle): "
          f"{'SUPPORTED' if h70b_supported else 'KILLED'}  "
          f"[n=2 UNSTABLE]")
    print(f"    word: BCa=[{ms_word_bca[0]:.4f}, {ms_word_bca[1]:.4f}] vs oracle={ms_word_oracle:.4f} "
          f"-> includes={h70b_word_includes}")
    print(f"    char: BCa=[{ms_char_bca[0]:.4f}, {ms_char_bca[1]:.4f}] vs oracle={ms_char_oracle:.4f} "
          f"-> includes={h70b_char_includes}")
    print(f"  H70c (per-mode width ratio > 1.5): "
          f"{'SUPPORTED' if h70c_supported else 'KILLED'}")
    print(f"    char ratio: {char_ratio:.4f} (min={char_wmin:.4f}@{char_kmin}, max={char_wmax:.4f}@{char_kmax})")
    print(f"    word ratio: {word_ratio:.4f} (min={word_wmin:.4f}@{word_kmin}, max={word_wmax:.4f}@{word_kmax})")
    print(f"    stable-only char ratio: {stable_char_ratio:.4f}")
    print(f"    stable-only word ratio: {stable_word_ratio:.4f}")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
