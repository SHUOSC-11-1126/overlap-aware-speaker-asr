#!/usr/bin/env python3
"""RQ31: Char-level cpWER re-validation of the corrected router.

RQ30 (PR #934) discovered that every prior routing study on AISHELL-4 (RQ1, RQ8,
RQ12, RQ13, RQ16, RQ25, RQ29) computed cpWER at the wrong granularity for
Chinese: whole speaker strings were passed to MeetEval as a single "word"
(no whitespace => 1 token per speaker), instead of the standard Chinese cpCER
convention where each character is a token. RQ30 showed this inflates the
separation tax ~80x and scrambles per-window ordering (Spearman rho ~ 0.1).

This study re-runs RQ16's corrected-router simulation at character level. The
corrected router here is RQ16's lang-id-entropy-only ablation (threshold 0.409
bits, RQ13's >=90%-specificity operating point): route to MIXED if
lang_id_entropy > 0.409, else SEPARATED. RQ16 found this single guard is
identical to the full three-guard corrected router on AISHELL-4 (the silence
and mode guards are redundant), so the lang-id-only router IS the corrected
router for this meeting.

Hypotheses (pre-registered)
---------------------------
- H31a: char-level corrected router cpWER < char-level always-mixed cpWER.
        SUPPORTED if cpWER_corrected < cpWER_mixed; KILL if >=.
- H31b: lang-id entropy detector recovers > 80% of the gap to oracle at char
        level. SUPPORTED if (mixed - corrected) / (mixed - oracle) > 0.80;
        KILL if <= 0.80.
- H31c: Mode S (monoscript-Chinese hallucinations, windows 22 and 30) still
        accounts for > 50% of the char-level residual. SUPPORTED if
        Mode S contribution / total residual > 0.50; KILL if <= 0.50.

Method
------
For each of the 77 AISHELL-4 windows we:
  1. Compute char-level cpWER with MeetEval 0.4.3's cpwer / orcwer using
     character-level tokenisation: ' '.join(list(text)) for each Chinese string
     (the standard cpCER convention, matching RQ30's char-level arm).
  2. Compute lang_id_entropy (RQ13 detector, verbatim) from the per-speaker
     separated transcripts, aggregated by MAX across speakers.
  3. Apply the corrected router: lang_id_entropy > 0.409 => MIXED, else
     SEPARATED. The per-window corrected cpWER is the chosen route's char-level
     cpWER.
  4. Compute five policies: always_mixed_char, always_separated_char,
     corrected_router_char, oracle_char (= min(mixed, separated)),
     router_v2_char (uses the stored router_v2_method choice).
  5. Mode S residual: per window residual = corrected_char - oracle_char;
     Mode S contribution = sum of residuals over windows 22 and 30.

Reanalysis only -- no Whisper / no ASR runs. Uses the stored transcripts in
results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json.

Label: experimental/frontier. Closes #938.

Run:
    /opt/homebrew/bin/python3 results/frontier/char_level_cpwer_revalidation/char_level_revalidation_analysis.py
"""
from __future__ import annotations

import csv
import json
import math
import unicodedata
import warnings
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")  # MeetEval prints "Assuming sort=False" spam

import numpy as np
from scipy.stats import spearmanr
import meeteval
from meeteval.wer import cpwer, orcwer

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
OUT_CSV = OUT_DIR / "char_level_revalidation_results.csv"
OUT_JSON = OUT_DIR / "char_level_revalidation_results.json"

SESSION_ID = "s1"

# ------------------------------------------------------------------ thresholds
# RQ13 calibrated operating point (>= 90% specificity on AISHELL-4 non-hallucinated
# tracks): threshold 0.409073, specificity 0.925, sensitivity 0.946. We use 0.409.
LANG_ID_ENTROPY_THRESHOLD = 0.409

N_BOOT = 10000
SEED = 42
EPS = 1e-9

# Mode S windows: monoscript-Chinese separated hallucinations that escape every
# reference-free guard (RQ16, FINDINGS.md). These are the corrected router's
# only losses vs always-mixed at word level.
MODE_S_WINDOWS = (22, 30)


# ------------------------------------------------------------- CR / script primitives
# Verbatim from RQ13 / RQ16 so thresholds are directly comparable.
def script_category(ch: str) -> str:
    """Map a character to a coarse Unicode script category (RQ13 verbatim).

    Uses unicodedata.name. Whitespace -> "Space"; punctuation/symbols -> "Punct";
    control/unknown -> "Other". Sufficient to separate Han / Latin / Hiragana /
    Katakana / Hangul / Cyrillic / Arabic / Greek / Digit.
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

    Clean Chinese (near-monoscript Han) -> entropy ~ 0. Diverse multilingual
    gibberish mixing Han+Latin+Katakana+Hangul -> high entropy."""
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


def max_across_speakers(window: dict[str, Any], fn) -> float:
    """Max of fn(text) over the per-speaker separated transcripts (worst-case).

    Same convention as RQ12/RQ13/RQ16: a window is flagged if ANY speaker track
    trips the detector. Empty/whitespace speaker texts are skipped."""
    vals = [
        fn(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


# ----------------------------------------------------------- MeetEval char-level
def to_char_level(text: str) -> str:
    """Space-separate each character so MeetEval treats it as one "word".

    Standard Chinese cpCER convention: Chinese has no word delimiter, so each
    character IS a token. Matches RQ30's char-level arm verbatim."""
    return " ".join(list(text))


def build_segments(speaker_text: dict[str, str]) -> list[dict]:
    """Build MeetEval char-level segment dicts from {speaker: text}.

    Skips empty/whitespace-only strings (matches the project's compute_cpwer
    and RQ30's build_segments)."""
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
    """Run cpwer; on empty input return the project's empty-sentinel (1.0, -1, -1)."""
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


# ------------------------------------------------------------- decision / routing
def corrected_router_decision(lang_id_entropy: float) -> str:
    """Corrected router (lang-id-only, = RQ16's full router on AISHELL-4).

    Route to MIXED if lang_id_entropy > 0.409, else SEPARATED. RQ16 showed the
    silence and mode guards are redundant once lang-id is in the ensemble, so
    lang-id-alone IS the corrected router for this meeting."""
    return "mixed" if lang_id_entropy > LANG_ID_ENTROPY_THRESHOLD else "separated"


def router_v2_decision(window: dict[str, Any]) -> str:
    """Router v2's stored per-window method choice ('mixed' or 'separated')."""
    return str(window["router_v2_method"])


def cpwer_for_route(mixed_char: float, separated_char: float, choice: str) -> float:
    """Return the char-level cpWER for the chosen route."""
    return mixed_char if choice == "mixed" else separated_char


# --------------------------------------------------------------------- bootstrap
def bootstrap_mean_ci(values: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED) -> tuple[float, float]:
    """Bootstrap 95% CI for the mean of values (resample with replacement)."""
    rng = np.random.default_rng(seed)
    n = len(values)
    means: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        means.append(float(values[idx].mean()))
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def bootstrap_diff_ci(
    a: np.ndarray, b: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED
) -> tuple[float, float]:
    """Bootstrap 95% CI for mean(a) - mean(b) (paired, per-window resample)."""
    rng = np.random.default_rng(seed)
    n = len(a)
    diffs: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        diffs.append(float(a[idx].mean() - b[idx].mean()))
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def bootstrap_recovery_ci(
    mixed: np.ndarray, corrected: np.ndarray, oracle: np.ndarray,
    n_boot: int = N_BOOT, seed: int = SEED,
) -> tuple[float, float]:
    """Bootstrap 95% CI for the recovery fraction (mixed - corrected) / (mixed - oracle).

    Computed per-resample from the resampled means. Guarded against zero
    denominator."""
    rng = np.random.default_rng(seed)
    n = len(mixed)
    recoveries: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        m = float(mixed[idx].mean())
        c = float(corrected[idx].mean())
        o = float(oracle[idx].mean())
        denom = m - o
        if denom > EPS:
            recoveries.append((m - c) / denom)
    if not recoveries:
        return 0.0, 0.0
    return float(np.percentile(recoveries, 2.5)), float(np.percentile(recoveries, 97.5))


def bootstrap_mode_s_share_ci(
    corrected: np.ndarray, oracle: np.ndarray, mode_s_idx: list[int],
    n_boot: int = N_BOOT, seed: int = SEED,
) -> tuple[float, float]:
    """Bootstrap 95% CI for Mode S share of total residual.

    residual_i = corrected_i - oracle_i (>= 0 since corrected >= oracle).
    Mode S share = sum(residual_i for i in mode_s_idx) / sum(residual_i).
    Guarded against zero total residual."""
    rng = np.random.default_rng(seed)
    n = len(corrected)
    residuals = corrected - oracle
    mode_s_mask = np.zeros(n, dtype=bool)
    for i in mode_s_idx:
        if 0 <= i < n:
            mode_s_mask[i] = True
    shares: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        res = residuals[idx]
        total = float(res.sum())
        mode_s = float(res[mode_s_mask[idx]].sum())
        if total > EPS:
            shares.append(mode_s / total)
    if not shares:
        return 0.0, 0.0
    return float(np.percentile(shares, 2.5)), float(np.percentile(shares, 97.5))


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]
    n = len(windows)

    # Per-window char-level cpWER + corrected-router decision.
    rows: list[dict[str, Any]] = []
    for w in windows:
        wid = w["window_id"]
        ref = w["ref_text_per_speaker"]
        hyp_sep = w["separated_text_per_speaker"]
        mixed_text = w["mixed_text"]
        router_v2_method = w["router_v2_method"]

        # Char-level MeetEval cpWER / orcWER.
        ref_segs = build_segments(ref)
        sep_segs = build_segments(hyp_sep)
        mix_segs = build_mixed_segment(mixed_text)

        separated_char, sep_err, sep_len = safe_cpwer(ref_segs, sep_segs)
        mixed_char, mix_err, mix_len = safe_orcwer(ref_segs, mix_segs)

        # Lang-id entropy detector (RQ13/RQ16, computed from separated text).
        ent = max_across_speakers(w, language_id_entropy)

        # Decisions.
        corr_choice = corrected_router_decision(ent)
        rv2_choice = router_v2_decision(w)

        # Policy cpWERs.
        corrected_char = cpwer_for_route(mixed_char, separated_char, corr_choice)
        oracle_char = min(mixed_char, separated_char)
        router_v2_char = cpwer_for_route(mixed_char, separated_char, rv2_choice)

        residual = corrected_char - oracle_char

        row: dict[str, Any] = {
            "window_id": wid,
            "overlap_ratio": w["overlap_ratio"],
            "overlap_label": w["overlap_label"],
            "num_speakers": w["num_speakers"],
            "router_v2_method": router_v2_method,
            "lang_id_entropy": round(ent, 6),
            "lang_id_flag": bool(ent > LANG_ID_ENTROPY_THRESHOLD),
            "corrected_decision": corr_choice,
            "always_mixed_char": round(mixed_char, 6),
            "always_separated_char": round(separated_char, 6),
            "corrected_router_char": round(corrected_char, 6),
            "oracle_char": round(oracle_char, 6),
            "router_v2_char": round(router_v2_char, 6),
            "residual_corrected_minus_oracle": round(residual, 6),
            "is_mode_s": wid in MODE_S_WINDOWS,
            "separated_char_errors": sep_err,
            "separated_char_length": sep_len,
            "mixed_char_errors": mix_err,
            "mixed_char_length": mix_len,
        }
        rows.append(row)

    # ---------------------------------------------------------- aggregate policies
    def policy_mean(key: str) -> float:
        return float(np.mean([r[key] for r in rows]))

    always_mixed_char = policy_mean("always_mixed_char")
    always_separated_char = policy_mean("always_separated_char")
    corrected_router_char = policy_mean("corrected_router_char")
    oracle_char = policy_mean("oracle_char")
    router_v2_char = policy_mean("router_v2_char")

    # Separation tax at char level.
    separation_tax_char = always_separated_char - always_mixed_char

    # Decision counts.
    corrected_counts = {"mixed": 0, "separated": 0}
    for r in rows:
        corrected_counts[r["corrected_decision"]] += 1

    # ---------------------------------------------------------- arrays for stats
    mixed_arr = np.array([r["always_mixed_char"] for r in rows], dtype=float)
    separated_arr = np.array([r["always_separated_char"] for r in rows], dtype=float)
    corrected_arr = np.array([r["corrected_router_char"] for r in rows], dtype=float)
    oracle_arr = np.array([r["oracle_char"] for r in rows], dtype=float)
    rv2_arr = np.array([r["router_v2_char"] for r in rows], dtype=float)

    # Bootstrap CIs.
    ci_corrected = bootstrap_mean_ci(corrected_arr)
    ci_mixed = bootstrap_mean_ci(mixed_arr)
    ci_separated = bootstrap_mean_ci(separated_arr)
    ci_oracle = bootstrap_mean_ci(oracle_arr)
    ci_rv2 = bootstrap_mean_ci(rv2_arr)

    ci_corrected_minus_mixed = bootstrap_diff_ci(corrected_arr, mixed_arr)
    ci_corrected_minus_rv2 = bootstrap_diff_ci(corrected_arr, rv2_arr)

    # ---------------------------------------------------------- H31b: recovery
    # recovery = (mixed - corrected) / (mixed - oracle)
    regret_gap_mixed_oracle = always_mixed_char - oracle_char
    regret_gap_corrected_oracle = corrected_router_char - oracle_char
    if regret_gap_mixed_oracle > EPS:
        recovery_fraction = (always_mixed_char - corrected_router_char) / regret_gap_mixed_oracle
    else:
        recovery_fraction = 0.0
    ci_recovery = bootstrap_recovery_ci(mixed_arr, corrected_arr, oracle_arr)

    # ---------------------------------------------------------- H31c: Mode S residual
    residuals = corrected_arr - oracle_arr
    total_residual = float(residuals.sum())
    mode_s_idx = [i for i, r in enumerate(rows) if r["is_mode_s"]]
    mode_s_residual = float(residuals[mode_s_idx].sum()) if mode_s_idx else 0.0
    if total_residual > EPS:
        mode_s_share = mode_s_residual / total_residual
    else:
        mode_s_share = 0.0
    ci_mode_s_share = bootstrap_mode_s_share_ci(
        corrected_arr, oracle_arr, [r["window_id"] for r in rows if r["is_mode_s"]]
    )

    # Per-window Mode S detail.
    mode_s_detail = [
        {
            "window_id": r["window_id"],
            "lang_id_entropy": r["lang_id_entropy"],
            "corrected_decision": r["corrected_decision"],
            "always_mixed_char": r["always_mixed_char"],
            "always_separated_char": r["always_separated_char"],
            "corrected_router_char": r["corrected_router_char"],
            "oracle_char": r["oracle_char"],
            "residual": r["residual_corrected_minus_oracle"],
        }
        for r in rows if r["is_mode_s"]
    ]

    # ---------------------------------------------------------- Spearman (word vs char)
    # Cross-check: stored word-level vs our char-level per-window ordering.
    stored_sep_er = [float(w["cpwer_separated"]["error_rate"]) for w in windows]
    stored_mixed_er = [float(w["orcwer_mixed"]["error_rate"]) for w in windows]
    rho_word_vs_char_sep = float(spearmanr(stored_sep_er, separated_arr)[0])
    rho_word_vs_char_mix = float(spearmanr(stored_mixed_er, mixed_arr)[0])

    # ---------------------------------------------------------- hypothesis verdicts
    h31a_supported = corrected_router_char < always_mixed_char
    h31b_supported = recovery_fraction > 0.80
    h31c_supported = mode_s_share > 0.50

    # Win/tie/loss of corrected router vs always-mixed (per window).
    wins = int(np.sum(corrected_arr < mixed_arr))
    ties = int(np.sum(np.isclose(corrected_arr, mixed_arr)))
    losses = int(np.sum(corrected_arr > mixed_arr))

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ31: Char-level cpWER re-validation of the corrected router",
        "closes_issue": 938,
        "meeteval_version": meeteval.__version__,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "method": (
            "reanalysis only (no Whisper / no ASR run); char-level cpWER computed "
            "with MeetEval 0.4.3 using character-level tokenisation "
            "(' '.join(list(text))). Corrected router = RQ16's lang-id-entropy-only "
            "ablation (threshold 0.409 bits): route MIXED if lang_id_entropy > 0.409, "
            "else SEPARATED. RQ16 showed this is identical to the full three-guard "
            "corrected router on AISHELL-4."
        ),
        "meeting_id": data["meeting_id"],
        "n_windows": n,
        "thresholds": {
            "lang_id_entropy": LANG_ID_ENTROPY_THRESHOLD,
            "note": (
                "lang_id_entropy threshold 0.409 from RQ13 (>=90% specificity, "
                "94.6% sensitivity). Corrected router here is lang-id-only, which "
                "RQ16 found identical to the full three-guard router on AISHELL-4."
            ),
        },
        "mode_s_windows": list(MODE_S_WINDOWS),
        "char_level_baselines": {
            "always_mixed_char": round(always_mixed_char, 6),
            "always_separated_char": round(always_separated_char, 6),
            "corrected_router_char": round(corrected_router_char, 6),
            "oracle_char": round(oracle_char, 6),
            "router_v2_char": round(router_v2_char, 6),
        },
        "char_level_ci_95": {
            "always_mixed_char": [round(ci_mixed[0], 6), round(ci_mixed[1], 6)],
            "always_separated_char": [round(ci_separated[0], 6), round(ci_separated[1], 6)],
            "corrected_router_char": [round(ci_corrected[0], 6), round(ci_corrected[1], 6)],
            "oracle_char": [round(ci_oracle[0], 6), round(ci_oracle[1], 6)],
            "router_v2_char": [round(ci_rv2[0], 6), round(ci_rv2[1], 6)],
        },
        "word_level_baselines_from_rq16": {
            "always_mixed_cpwer": 1.17316,
            "always_separated_cpwer": 1.590909,
            "corrected_router_cpwer": 1.04329,
            "router_v2_cpwer": 1.205628,
            "oracle_best_cpwer": 1.017316,
        },
        "separation_tax": {
            "word_level": round(1.590909 - 1.17316, 6),
            "char_level": round(separation_tax_char, 6),
            "ratio_word_over_char": round(
                (1.590909 - 1.17316) / separation_tax_char, 2
            ) if abs(separation_tax_char) > EPS else None,
        },
        "corrected_router_decision_counts": corrected_counts,
        "corrected_vs_mixed_win_tie_loss": {"wins": wins, "ties": ties, "losses": losses},
        "regret_analysis": {
            "mixed_regret_gap_to_oracle_char": round(regret_gap_mixed_oracle, 6),
            "corrected_regret_gap_to_oracle_char": round(regret_gap_corrected_oracle, 6),
            "corrected_recovery_fraction": round(recovery_fraction, 6),
            "corrected_recovery_ci_95": [round(ci_recovery[0], 6), round(ci_recovery[1], 6)],
            "corrected_minus_mixed_delta": round(corrected_router_char - always_mixed_char, 6),
            "corrected_minus_mixed_ci_95": [
                round(ci_corrected_minus_mixed[0], 6),
                round(ci_corrected_minus_mixed[1], 6),
            ],
            "corrected_minus_router_v2_delta": round(corrected_router_char - router_v2_char, 6),
            "corrected_minus_router_v2_ci_95": [
                round(ci_corrected_minus_rv2[0], 6),
                round(ci_corrected_minus_rv2[1], 6),
            ],
        },
        "mode_s_analysis": {
            "mode_s_windows": list(MODE_S_WINDOWS),
            "total_residual_char": round(total_residual, 6),
            "mode_s_residual_char": round(mode_s_residual, 6),
            "mode_s_share_of_residual": round(mode_s_share, 6),
            "mode_s_share_ci_95": [round(ci_mode_s_share[0], 6), round(ci_mode_s_share[1], 6)],
            "mode_s_per_window": mode_s_detail,
        },
        "per_window_spearman_word_vs_char": {
            "separated": {
                "rho": round(rho_word_vs_char_sep, 6),
                "interpretation": "does word-level preserve char-level per-window ordering? (RQ30: no)",
            },
            "mixed": {
                "rho": round(rho_word_vs_char_mix, 6),
                "interpretation": "does word-level preserve char-level per-window ordering? (RQ30: no)",
            },
        },
        "hypothesis_verdicts": {
            "H31a": {
                "statement": "char-level corrected router cpWER < char-level always-mixed cpWER",
                "corrected_router_char": round(corrected_router_char, 6),
                "always_mixed_char": round(always_mixed_char, 6),
                "delta_corrected_minus_mixed": round(corrected_router_char - always_mixed_char, 6),
                "bootstrap_ci_95": [
                    round(ci_corrected_minus_mixed[0], 6),
                    round(ci_corrected_minus_mixed[1], 6),
                ],
                "success_criterion": "cpWER_corrected < cpWER_mixed",
                "kill_criterion": "cpWER_corrected >= cpWER_mixed",
                "supported": bool(h31a_supported),
            },
            "H31b": {
                "statement": "lang-id entropy detector recovers > 80% of gap to oracle at char level",
                "recovery_fraction": round(recovery_fraction, 6),
                "formula": "(mixed - corrected) / (mixed - oracle)",
                "mixed_char": round(always_mixed_char, 6),
                "corrected_char": round(corrected_router_char, 6),
                "oracle_char": round(oracle_char, 6),
                "bootstrap_ci_95": [round(ci_recovery[0], 6), round(ci_recovery[1], 6)],
                "success_criterion": "ratio > 0.80",
                "kill_criterion": "ratio <= 0.80",
                "supported": bool(h31b_supported),
            },
            "H31c": {
                "statement": "Mode S (windows 22, 30) accounts for > 50% of char-level residual",
                "mode_s_share_of_residual": round(mode_s_share, 6),
                "mode_s_residual_char": round(mode_s_residual, 6),
                "total_residual_char": round(total_residual, 6),
                "bootstrap_ci_95": [round(ci_mode_s_share[0], 6), round(ci_mode_s_share[1], 6)],
                "success_criterion": "Mode S contribution / total residual > 0.50",
                "kill_criterion": "ratio <= 0.50",
                "supported": bool(h31c_supported),
            },
        },
    }

    # ----------------------------------------------------------- write CSV
    csv_fields = [
        "window_id", "overlap_ratio", "overlap_label", "num_speakers",
        "router_v2_method", "lang_id_entropy", "lang_id_flag",
        "corrected_decision",
        "always_mixed_char", "always_separated_char",
        "corrected_router_char", "oracle_char", "router_v2_char",
        "residual_corrected_minus_oracle", "is_mode_s",
        "separated_char_errors", "separated_char_length",
        "mixed_char_errors", "mixed_char_length",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, "") for k in csv_fields})

    # ----------------------------------------------------------- write JSON
    summary_with_rows = dict(summary)
    summary_with_rows["per_window"] = rows
    OUT_JSON.write_text(
        json.dumps(summary_with_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # ----------------------------------------------------------- console
    print(f"=== RQ31: Char-level cpWER re-validation of the corrected router ===")
    print(f"Label: experimental/frontier  |  MeetEval {meeteval.__version__}")
    print(f"Source: {SRC_JSON.relative_to(PROJECT_ROOT)}  |  Windows: {n}")
    print()
    print("Char-level cpWER (mean over 77 windows, 95% bootstrap CI):")
    print(f"  always_mixed      : {always_mixed_char:.6f}  CI=[{ci_mixed[0]:.4f}, {ci_mixed[1]:.4f}]")
    print(f"  always_separated  : {always_separated_char:.6f}  CI=[{ci_separated[0]:.4f}, {ci_separated[1]:.4f}]")
    print(f"  router_v2         : {router_v2_char:.6f}  CI=[{ci_rv2[0]:.4f}, {ci_rv2[1]:.4f}]")
    print(f"  corrected router  : {corrected_router_char:.6f}  CI=[{ci_corrected[0]:.4f}, {ci_corrected[1]:.4f}]")
    print(f"  oracle best       : {oracle_char:.6f}  CI=[{ci_oracle[0]:.4f}, {ci_oracle[1]:.4f}]")
    print()
    print(f"Separation tax (sep - mixed): word={1.590909-1.17316:.6f}  char={separation_tax_char:.6f}")
    print()
    print(f"Corrected router decisions: mixed={corrected_counts['mixed']}, "
          f"separated={corrected_counts['separated']}")
    print(f"Corrected vs always-mixed: {wins} wins, {ties} ties, {losses} losses")
    print()
    print("Hypothesis verdicts:")
    print(f"  H31a (corrected_char < mixed_char): "
          f"{'SUPPORTED' if h31a_supported else 'NOT SUPPORTED'}  "
          f"(delta={corrected_router_char-always_mixed_char:+.6f}, "
          f"CI=[{ci_corrected_minus_mixed[0]:+.4f}, {ci_corrected_minus_mixed[1]:+.4f}])")
    print(f"  H31b (recovery > 80% of mixed->oracle gap): "
          f"{'SUPPORTED' if h31b_supported else 'NOT SUPPORTED'}  "
          f"(recovery={recovery_fraction:.1%}, CI=[{ci_recovery[0]:.1%}, {ci_recovery[1]:.1%}])")
    print(f"  H31c (Mode S > 50% of residual): "
          f"{'SUPPORTED' if h31c_supported else 'NOT SUPPORTED'}  "
          f"(share={mode_s_share:.1%}, CI=[{ci_mode_s_share[0]:.1%}, {ci_mode_s_share[1]:.1%}])")
    print()
    print(f"Mode S detail (windows {MODE_S_WINDOWS}):")
    for d in mode_s_detail:
        print(f"  window {d['window_id']}: ent={d['lang_id_entropy']:.3f} "
              f"decision={d['corrected_decision']} "
              f"mixed={d['always_mixed_char']:.4f} sep={d['always_separated_char']:.4f} "
              f"corrected={d['corrected_router_char']:.4f} oracle={d['oracle_char']:.4f} "
              f"residual={d['residual']:.4f}")
    print()
    print(f"Per-window Spearman (word vs char): separated rho={rho_word_vs_char_sep:+.4f}, "
          f"mixed rho={rho_word_vs_char_mix:+.4f}")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
