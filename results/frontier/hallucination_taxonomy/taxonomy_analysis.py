"""RQ14: Hallucination taxonomy on AISHELL-4 — characterizing the 37 hallucinated
separated tracks.

REANALYSIS ONLY — no Whisper / no ASR model is run. This script reads the existing
AISHELL-4 external-validation results (``results/external_sanity_check/aishell4/
rq1_aishell4_validation_results.json``, label ``external/sanity-check``, PR #890) and
classifies each of the 37 windows whose separated track hallucinated (cpWER > 1.0,
per RQ12 / finding #23) into a finer, mutually exclusive hallucination mode.

Label: experimental/frontier
Closes #902. Builds on RQ12 (``results/frontier/router_failure_modes/``, PR #900),
which found 37 / 77 separated tracks hallucinate but lumped 36 of them as a single
"CR-missed (diverse)" bucket. This module decomposes that bucket.

Research questions
------------------
1. What is the mode mix of the 37 hallucinated separated tracks?
2. Do the modes have distinct reference-free detector profiles (CR, language-id
   entropy, TTR)?
3. Does any single reference-free detector catch the majority of hallucination?

Hypotheses
----------
- H14a: multilingual mixing accounts for > 50% of hallucinated separated tracks.
- H14b: repetition (CR > 2.4) accounts for < 10% of hallucinated separated tracks.
- H14c: the modes have distinct CR profiles (between-mode CR variance exceeds the
  permutation null at p < 0.05).

Method
------
For each hallucinated window (always_separated_cpwer > 1.0) we compute, from the
stored per-speaker separated transcript text only (no audio, no Whisper):

  - max CR across per-speaker CONCATENATED separated text (Whisper-style
    ``len(utf8)/len(zlib)``; LOWER BOUND on Whisper's per-segment max CR, same proxy
    as RQ12).
  - distinct Unicode script count (Han / Latin / Hiragana / Katakana / Hangul).
  - Shannon entropy (bits) over the 6-bucket script distribution (language-id
    entropy; 0 = single script, log2(6) ~= 2.586 = uniform over 6 scripts).
  - character type-token ratio (TTR) over non-whitespace chars (excluding Whisper
    ``<|...|>`` tag artifacts); low TTR = repetitive, high TTR = diverse.
  - length ratio = separated_total_length / max(mixed_text_length, 1). When the
    mixed track is empty this is large, flagging the separated track inserted a long
    transcript where the mixed decoder produced nothing.

Primary mode assignment is mutually exclusive, by precedence:

  1. multilingual_mixing      : >= 3 distinct scripts (Han + Latin + any of
                                Hiragana/Katakana/Hangul, etc.)
  2. repetition               : max CR > 2.4 (Whisper default; Mode R, finding #21)
  3. insertion_dominated      : length ratio > 2.0  (separated >> mixed; word
                                insertion / long hallucination vs short/empty mixed)
  4. substitution_dominated   : 1.0 <= length ratio <= 2.0 (comparable length,
                                high char count relative to mixed => substitutions)
  5. semantic_drift           : length ratio < 1.0 (moderate/short length, single
                                script, not repetition; semantically unrelated)

The length-ratio cut at 2.0 is a documented heuristic; there is a clean gap in the
data between ~1.7 and ~2.4 (and 3.3+ for clearly longer separated tracks). When
mixed_text_length == 0 the ratio collapses to separated_total_length, which is
always >> 2.0 for the hallucinated windows, so those fall into insertion_dominated
(long hallucinated transcript where the mixed decoder emitted nothing).

This script is pure reanalysis (numpy + stdlib only; scipy is NOT required).
"""
from __future__ import annotations

import csv
import json
import math
import re
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
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "hallucination_taxonomy"
OUT_CSV = OUT_DIR / "taxonomy_results.csv"
OUT_JSON = OUT_DIR / "taxonomy_results.json"

# ------------------------------------------------------------------ thresholds
CR_THRESHOLD = 2.4              # Whisper default compression_ratio_threshold
CATASTROPHIC_CPWER = 1.0        # cpWER > 1.0 => insertions dominate (hallucination)
MULTILINGUAL_SCRIPT_MIN = 3     # >= 3 distinct scripts => multilingual mixing
INSERTION_RATIO = 2.0           # separated/mixed length ratio above this => insertion
SUBST_RATIO_LO = 1.0            # >= this (and <= INSERTION_RATIO) => substitution
LANG_ENTROPY_THRESHOLD = 0.5    # bits; ~10% minority script in a 2-script mix
TTR_THRESHOLD = 0.7             # character TTR above this => diverse
N_BOOT = 10000
N_PERM = 10000
SEED = 42
EPS = 1e-9

# Whisper tag artifacts like <|lv|> / <|zh|> / <|en|> — strip before char stats.
_WHISPER_TAG_RE = re.compile(r"<\|[^|]*\|>")
# Separators embedded in some transcripts.
_SEP_RE = re.compile(r"<#>")


# ----------------------------------------------------------------- CR primitive
def compression_ratio(text: str) -> float:
    """Whisper-style compression ratio: len(utf8 bytes) / len(zlib-compressed bytes).

    Matches ``whisper.audio.compression_ratio``. Returns 0.0 for empty/whitespace
    text. High CR (>~2.4) indicates a repetitive / degenerate loop."""
    if not text or not text.strip():
        return 0.0
    b = text.encode("utf-8")
    c = zlib.compress(b)
    return len(b) / len(c) if len(c) > 0 else 0.0


def max_cr_separated(window: dict[str, Any]) -> float:
    """Max Whisper CR across the per-speaker separated transcripts.

    Same LOWER-BOUND proxy as RQ12: the stored text is the per-speaker CONCATENATED
    transcript, which dilutes CR relative to Whisper's true per-segment max CR."""
    vals = [
        compression_ratio(t)
        for t in window.get("separated_text_per_speaker", {}).values()
        if t and str(t).strip()
    ]
    return max(vals) if vals else 0.0


# ----------------------------------------------------------- script statistics
def _script_bucket(ch: str) -> str | None:
    """Return the language-script bucket for a char, or None for non-language chars."""
    cp = ord(ch)
    if (0x4E00 <= cp <= 0x9FFF) or (0x3400 <= cp <= 0x4DBF) or (0xF900 <= cp <= 0xFAFF):
        return "Han"
    if 0x3040 <= cp <= 0x309F:
        return "Hiragana"
    if 0x30A0 <= cp <= 0x30FF:
        return "Katakana"
    if (0xAC00 <= cp <= 0xD7AF) or (0x1100 <= cp <= 0x11FF) or (0x3130 <= cp <= 0x318F):
        return "Hangul"
    if (0x0041 <= cp <= 0x005A) or (0x0061 <= cp <= 0x007A):
        return "Latin"
    return None  # digits, punctuation, emoji, whitespace, etc. are not language scripts


def distinct_scripts(text: str) -> set[str]:
    """Distinct language-script buckets present (excludes non-language chars)."""
    out: set[str] = set()
    for ch in text:
        b = _script_bucket(ch)
        if b is not None:
            out.add(b)
    return out


def script_distribution(text: str) -> dict[str, int]:
    """Per-bucket character counts over the 6 language scripts + 'Other'."""
    dist: dict[str, int] = {
        "Han": 0, "Latin": 0, "Hiragana": 0, "Katakana": 0, "Hangul": 0, "Other": 0,
    }
    for ch in text:
        b = _script_bucket(ch)
        if b is None:
            dist["Other"] += 1
        else:
            dist[b] += 1
    return dist


def shannon_entropy(dist: dict[str, int]) -> float:
    """Shannon entropy (bits) over the script distribution.

    Computed over all 6 buckets + 'Other' so a single-script track has entropy 0
    and a uniform mix across k scripts has entropy log2(k)."""
    total = sum(dist.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for v in dist.values():
        if v > 0:
            p = v / total
            h -= p * math.log2(p)
    return h


def char_ttr(text: str) -> float:
    """Character type-token ratio over non-whitespace chars (Whisper tags stripped).

    TTR = |distinct chars| / |total chars|. Low TTR => repetitive; high TTR => diverse.
    Returns 0.0 for empty text."""
    cleaned = _WHISPER_TAG_RE.sub("", text)
    cleaned = _SEP_RE.sub("", cleaned)
    chars = [c for c in cleaned if not c.isspace()]
    if not chars:
        return 0.0
    return len(set(chars)) / len(chars)


def separated_text_concat(window: dict[str, Any]) -> str:
    """Concatenate per-speaker separated transcripts (space-joined)."""
    parts = [
        str(t) for t in window.get("separated_text_per_speaker", {}).values()
        if t and str(t).strip()
    ]
    return " ".join(parts)


# --------------------------------------------------------------- classification
def classify(window: dict[str, Any]) -> dict[str, Any]:
    """Compute all reference-free features + a mutually exclusive primary mode.

    A window is a *hallucinated separated track* iff always_separated_cpwer > 1.0
    (matches RQ12's 37-track set). Primary-mode precedence:

      1. multilingual_mixing  — distinct_scripts >= 3
      2. repetition           — max_cr_separated > 2.4 (Mode R, finding #21)
      3. insertion_dominated  — length_ratio > 2.0
      4. substitution_dominated — 1.0 <= length_ratio <= 2.0
      5. semantic_drift       — length_ratio < 1.0 (residual)

    The length_ratio is separated_total_length / max(mixed_text_length, 1). When the
    mixed track is empty this is large, so long hallucinated transcripts (the common
    silence-gap case) classify as insertion_dominated."""
    sep_text = separated_text_concat(window)
    mcr = max_cr_separated(window)
    scripts = distinct_scripts(sep_text)
    n_scripts = len(scripts)
    lang_h = shannon_entropy(script_distribution(sep_text))
    ttr = char_ttr(sep_text)
    sep_len = int(window.get("separated_total_length", 0) or 0)
    mix_len = int(window.get("mixed_text_length", 0) or 0)
    ratio = sep_len / max(mix_len, 1)

    # Mutually exclusive primary mode by precedence.
    if n_scripts >= MULTILINGUAL_SCRIPT_MIN:
        mode = "multilingual_mixing"
    elif mcr > CR_THRESHOLD:
        mode = "repetition"
    elif ratio > INSERTION_RATIO:
        mode = "insertion_dominated"
    elif ratio >= SUBST_RATIO_LO:
        mode = "substitution_dominated"
    else:
        mode = "semantic_drift"

    return {
        "separated_cpwer": round(float(window["always_separated_cpwer"]), 6),
        "mixed_cpwer": round(float(window["always_mixed_cpwer"]), 6),
        "max_cr_separated": round(mcr, 4),
        "num_scripts": n_scripts,
        "scripts": ",".join(sorted(scripts)),
        "lang_entropy_bits": round(lang_h, 4),
        "char_ttr": round(ttr, 4),
        "separated_total_length": sep_len,
        "mixed_text_length": mix_len,
        "length_ratio": round(ratio, 4),
        "primary_mode": mode,
    }


# ----------------------------------------------------------------- bootstrap
def bootstrap_mode_proportions(
    modes: list[str],
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> dict[str, tuple[float, float]]:
    """Bootstrap 95% CI for each mode's proportion (n_mode / n_hallucinated).

    Resamples the n_hallucinated tracks with replacement and recomputes each mode's
    share. CIs are wide because n=37 and some modes are small — reported honestly."""
    rng = np.random.default_rng(seed)
    n = len(modes)
    mode_arr = np.array(modes)
    unique = sorted(set(modes))
    cis: dict[str, tuple[float, float]] = {}
    for m in unique:
        flag = np.array([1.0 if x == m else 0.0 for x in modes])
        fracs: list[float] = []
        for _ in range(n_boot):
            idx = rng.integers(0, n, size=n)
            fracs.append(float(flag[idx].mean()))
        cis[m] = (float(np.percentile(fracs, 2.5)), float(np.percentile(fracs, 97.5)))
    return cis


def bootstrap_mean(values: list[float], n_boot: int = N_BOOT, seed: int = SEED) -> tuple[float, float]:
    """Bootstrap 95% CI for the mean of a list of floats."""
    if not values:
        return 0.0, 0.0
    rng = np.random.default_rng(seed)
    arr = np.array(values, dtype=float)
    n = len(arr)
    means: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        means.append(float(arr[idx].mean()))
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def permutation_test_cr_profiles(
    cr_values: list[float],
    mode_labels: list[str],
    n_perm: int = N_PERM,
    seed: int = SEED,
) -> tuple[float, float, float]:
    """Permutation test for H14c (distinct CR profiles per mode).

    Statistic = between-group sum of squares of CR = sum_mode n_mode *
    (mean_cr_mode - grand_mean)^2. Under the null (modes are exchangeable) we
    permute the mode labels and recompute the statistic. p = fraction of null >=
    observed.

    Returns (observed_stat, null_mean, p_value)."""
    cr = np.array(cr_values, dtype=float)
    labels = np.array(mode_labels)
    n = len(cr)
    grand_mean = cr.mean() if n > 0 else 0.0

    def bss(lab: np.ndarray) -> float:
        total = 0.0
        for m in np.unique(lab):
            mask = lab == m
            cnt = int(mask.sum())
            if cnt == 0:
                continue
            mean_m = float(cr[mask].mean())
            total += cnt * (mean_m - grand_mean) ** 2
        return total

    observed = bss(labels)
    rng = np.random.default_rng(seed)
    null_stats = np.empty(n_perm, dtype=float)
    for i in range(n_perm):
        perm = rng.permutation(labels)
        null_stats[i] = bss(perm)
    p_val = float((null_stats >= observed).sum() / n_perm)
    return observed, float(null_stats.mean()), p_val


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]

    # Compute features for every window; keep the hallucinated separated tracks.
    all_rows: list[dict[str, Any]] = []
    for w in windows:
        feats = classify(w)
        all_rows.append({
            "window_id": w["window_id"],
            "window_start_sec": w["window_start_sec"],
            "overlap_level": w["overlap_level"],
            "overlap_label": w["overlap_label"],
            "num_speakers": w["num_speakers"],
            **feats,
        })

    halluc_rows = [r for r in all_rows if r["separated_cpwer"] > CATASTROPHIC_CPWER]
    n_halluc = len(halluc_rows)
    n_total = len(all_rows)

    mode_order = [
        "multilingual_mixing",
        "repetition",
        "insertion_dominated",
        "substitution_dominated",
        "semantic_drift",
    ]

    # Per-mode stats.
    mode_stats: dict[str, dict[str, Any]] = {}
    for m in mode_order:
        mrows = [r for r in halluc_rows if r["primary_mode"] == m]
        n_m = len(mrows)
        prop = n_m / n_halluc if n_halluc else 0.0
        cpwers = [r["separated_cpwer"] for r in mrows]
        crs = [r["max_cr_separated"] for r in mrows]
        ttrs = [r["char_ttr"] for r in mrows]
        ents = [r["lang_entropy_bits"] for r in mrows]
        mean_cpwer = float(np.mean(cpwers)) if cpwers else 0.0
        mean_cr = float(np.mean(crs)) if crs else 0.0
        mean_ttr = float(np.mean(ttrs)) if ttrs else 0.0
        mean_ent = float(np.mean(ents)) if ents else 0.0
        cr_ci = bootstrap_mean(crs) if crs else (0.0, 0.0)
        mode_stats[m] = {
            "count": n_m,
            "proportion": round(prop, 6),
            "mean_cpwer": round(mean_cpwer, 6),
            "mean_cr": round(mean_cr, 6),
            "mean_cr_ci_95": [round(cr_ci[0], 6), round(cr_ci[1], 6)],
            "mean_ttr": round(mean_ttr, 6),
            "mean_lang_entropy_bits": round(mean_ent, 6),
        }

    # Bootstrap CIs on mode proportions.
    mode_list = [r["primary_mode"] for r in halluc_rows]
    prop_cis = bootstrap_mode_proportions(mode_list)
    for m in mode_order:
        lo, hi = prop_cis.get(m, (0.0, 0.0))
        mode_stats[m]["proportion_ci_95"] = [round(lo, 6), round(hi, 6)]

    # Detector detectability matrix: for each mode, fraction caught by each detector.
    detectability: dict[str, dict[str, Any]] = {}
    for m in mode_order:
        mrows = [r for r in halluc_rows if r["primary_mode"] == m]
        n_m = len(mrows)
        if n_m == 0:
            detectability[m] = {
                "n": 0,
                "cr_gt_2.4": 0.0,
                "lang_entropy_gt_0.5": 0.0,
                "ttr_gt_0.7": 0.0,
                "any_detector": 0.0,
            }
            continue
        cr_caught = sum(1 for r in mrows if r["max_cr_separated"] > CR_THRESHOLD)
        ent_caught = sum(1 for r in mrows if r["lang_entropy_bits"] > LANG_ENTROPY_THRESHOLD)
        ttr_caught = sum(1 for r in mrows if r["char_ttr"] > TTR_THRESHOLD)
        any_caught = sum(
            1 for r in mrows
            if r["max_cr_separated"] > CR_THRESHOLD
            or r["lang_entropy_bits"] > LANG_ENTROPY_THRESHOLD
            or r["char_ttr"] > TTR_THRESHOLD
        )
        detectability[m] = {
            "n": n_m,
            "cr_gt_2.4": round(cr_caught / n_m, 6),
            "lang_entropy_gt_0.5": round(ent_caught / n_m, 6),
            "ttr_gt_0.7": round(ttr_caught / n_m, 6),
            "any_detector": round(any_caught / n_m, 6),
        }

    # Overall detector coverage across all 37 hallucinated tracks.
    overall_detect = {
        "n": n_halluc,
        "cr_gt_2.4": round(sum(1 for r in halluc_rows if r["max_cr_separated"] > CR_THRESHOLD) / n_halluc, 6),
        "lang_entropy_gt_0.5": round(sum(1 for r in halluc_rows if r["lang_entropy_bits"] > LANG_ENTROPY_THRESHOLD) / n_halluc, 6),
        "ttr_gt_0.7": round(sum(1 for r in halluc_rows if r["char_ttr"] > TTR_THRESHOLD) / n_halluc, 6),
        "any_detector": round(sum(1 for r in halluc_rows if (
            r["max_cr_separated"] > CR_THRESHOLD
            or r["lang_entropy_bits"] > LANG_ENTROPY_THRESHOLD
            or r["char_ttr"] > TTR_THRESHOLD
        )) / n_halluc, 6),
    }

    # Hypothesis verdicts.
    multilingual_prop = mode_stats["multilingual_mixing"]["proportion"]
    repetition_prop = mode_stats["repetition"]["proportion"]
    h14a_supported = bool(multilingual_prop > 0.5)
    h14b_supported = bool(repetition_prop < 0.10)

    cr_values = [r["max_cr_separated"] for r in halluc_rows]
    mode_labels = [r["primary_mode"] for r in halluc_rows]
    obs_bss, null_mean, h14c_p = permutation_test_cr_profiles(cr_values, mode_labels)
    h14c_supported = bool(h14c_p < 0.05)

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ14: Hallucination taxonomy on AISHELL-4 (37 hallucinated separated tracks)",
        "closes_issue": 902,
        "builds_on": "RQ12 (results/frontier/router_failure_modes/, PR #900)",
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "method": (
            "reanalysis only (no Whisper / no ASR run); CR recomputed from stored text "
            "via zlib; script counts / entropy / TTR from per-speaker concatenated "
            "separated text; numpy + stdlib only"
        ),
        "meeting_id": data["meeting_id"],
        "n_windows": n_total,
        "n_hallucinated_separated": n_halluc,
        "hallucination_definition": "always_separated_cpwer > 1.0 (matches RQ12)",
        "thresholds": {
            "cr_threshold": CR_THRESHOLD,
            "multilingual_script_min": MULTILINGUAL_SCRIPT_MIN,
            "insertion_length_ratio": INSERTION_RATIO,
            "substitution_length_ratio_lo": SUBST_RATIO_LO,
            "lang_entropy_bits": LANG_ENTROPY_THRESHOLD,
            "ttr_threshold": TTR_THRESHOLD,
        },
        "mode_precedence": [
            "1. multilingual_mixing (>= 3 distinct scripts)",
            "2. repetition (max CR > 2.4)",
            "3. insertion_dominated (length_ratio > 2.0)",
            "4. substitution_dominated (1.0 <= length_ratio <= 2.0)",
            "5. semantic_drift (length_ratio < 1.0)",
        ],
        "cr_proxy_note": (
            "max CR across per-speaker CONCATENATED separated text (lower bound on "
            "Whisper's per-segment max CR; same proxy as RQ12, conservative for CR "
            "sensitivity)"
        ),
        "length_ratio_note": (
            "separated_total_length / max(mixed_text_length, 1). When the mixed track "
            "is empty (common at NoOverlap silence gaps) this collapses to "
            "separated_total_length, which is >> 2.0 for hallucinated windows, so "
            "those long-transcript cases classify as insertion_dominated. The 2.0 "
            "cut sits in an empirical gap in the data (no ratios between ~1.7 and "
            "~2.4 except a few clearly-longer outliers)."
        ),
        "mode_stats": mode_stats,
        "detectability_matrix": detectability,
        "overall_detector_coverage": overall_detect,
        "hypothesis_verdicts": {
            "H14a": {
                "statement": "multilingual mixing > 50% of hallucinated separated tracks",
                "multilingual_proportion": round(multilingual_prop, 6),
                "multilingual_ci_95": mode_stats["multilingual_mixing"]["proportion_ci_95"],
                "supported": h14a_supported,
            },
            "H14b": {
                "statement": "repetition (CR > 2.4) < 10% of hallucinated separated tracks",
                "repetition_proportion": round(repetition_prop, 6),
                "repetition_ci_95": mode_stats["repetition"]["proportion_ci_95"],
                "supported": h14b_supported,
            },
            "H14c": {
                "statement": "modes have distinct CR profiles (permutation p < 0.05)",
                "observed_between_group_ss": round(obs_bss, 6),
                "null_mean_between_group_ss": round(null_mean, 6),
                "permutation_p_value": round(h14c_p, 6),
                "n_permutations": N_PERM,
                "supported": h14c_supported,
            },
        },
        "limitations": [
            "Single meeting (M_R003S02C01); n=37 hallucinated tracks; bootstrap CIs "
            "on mode proportions are wide (some modes have 1-4 members).",
            "Mode assignment uses documented length-ratio heuristics; the "
            "substitution/insertion boundary (ratio=2.0) and substitution/drift "
            "boundary (ratio=1.0) are approximate operational cuts, not validated "
            "categories.",
            "CR is a lower-bound proxy on concatenated per-speaker text (see RQ12); "
            "true Whisper per-segment CR may be higher, so repetition-mode "
            "undercount is conservative.",
            "Language-id entropy is script-based, not a true language identifier; it "
            "cannot distinguish e.g. English-only from Han-only drift within a "
            "single script.",
            "Semantic drift is a residual catch-all (single-script, not repetition, "
            "short relative to mixed); 'semantically unrelated' is not measured "
            "directly (no embeddings) — it is inferred from low length ratio + "
            "single script.",
            "Oracle-TextGrid separation; a real separator may produce a different "
            "mode mix. Whisper-tiny only.",
        ],
    }

    # Write CSV (per-window, hallucinated only).
    csv_fields = [
        "window_id", "window_start_sec", "overlap_level", "overlap_label",
        "num_speakers", "separated_cpwer", "mixed_cpwer", "max_cr_separated",
        "num_scripts", "scripts", "lang_entropy_bits", "char_ttr",
        "separated_total_length", "mixed_text_length", "length_ratio", "primary_mode",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        for r in halluc_rows:
            w.writerow({k: r.get(k, "") for k in csv_fields})

    # Write JSON (summary).
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ----------------------------------------------------------------- console
    print(f"=== RQ14: Hallucination taxonomy on AISHELL-4 ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Hallucinated separated tracks: {n_halluc}/{n_total} "
          f"(always_separated_cpwer > 1.0, matches RQ12)")
    print()
    print("Mode mix (mutually exclusive, by precedence):")
    print(f"  {'mode':28s} {'n':>3s} {'prop':>7s} {'meanCPWER':>10s} {'meanCR':>7s} "
          f"{'meanTTR':>8s} {'meanEnt':>8s}  CI95(prop)")
    for m in mode_order:
        s = mode_stats[m]
        ci = s["proportion_ci_95"]
        print(f"  {m:28s} {s['count']:3d} {s['proportion']:7.1%} "
              f"{s['mean_cpwer']:10.3f} {s['mean_cr']:7.3f} {s['mean_ttr']:8.3f} "
              f"{s['mean_lang_entropy_bits']:8.3f}  [{ci[0]:.1%}, {ci[1]:.1%}]")
    print()
    print("Detector detectability matrix (fraction of mode caught):")
    print(f"  {'mode':28s} {'n':>3s} {'CR>2.4':>7s} {'Ent>0.5':>8s} {'TTR>0.7':>8s} {'any':>6s}")
    for m in mode_order:
        d = detectability[m]
        print(f"  {m:28s} {d['n']:3d} {d['cr_gt_2.4']:7.1%} "
              f"{d['lang_entropy_gt_0.5']:8.1%} {d['ttr_gt_0.7']:8.1%} "
              f"{d['any_detector']:6.1%}")
    print(f"  {'OVERALL':28s} {overall_detect['n']:3d} {overall_detect['cr_gt_2.4']:7.1%} "
          f"{overall_detect['lang_entropy_gt_0.5']:8.1%} "
          f"{overall_detect['ttr_gt_0.7']:8.1%} "
          f"{overall_detect['any_detector']:6.1%}")
    print()
    print("Hypothesis verdicts:")
    print(f"  H14a (multilingual > 50%): "
          f"{'SUPPORTED' if h14a_supported else 'NOT SUPPORTED'} "
          f"(prop={multilingual_prop:.1%}, CI=[{mode_stats['multilingual_mixing']['proportion_ci_95'][0]:.1%}, "
          f"{mode_stats['multilingual_mixing']['proportion_ci_95'][1]:.1%}])")
    print(f"  H14b (repetition < 10%): "
          f"{'SUPPORTED' if h14b_supported else 'NOT SUPPORTED'} "
          f"(prop={repetition_prop:.1%}, CI=[{mode_stats['repetition']['proportion_ci_95'][0]:.1%}, "
          f"{mode_stats['repetition']['proportion_ci_95'][1]:.1%}])")
    print(f"  H14c (distinct CR profiles, perm p<0.05): "
          f"{'SUPPORTED' if h14c_supported else 'NOT SUPPORTED'} "
          f"(obs_BSS={obs_bss:.4f}, null_mean={null_mean:.4f}, p={h14c_p:.4f})")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
